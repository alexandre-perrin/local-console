import json
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import Callable
from typing import Optional

import trio
from kivymd.app import MDApp
from local_console.clients.agent import Agent
from local_console.clients.agent import check_attributes_request
from local_console.core.camera import Camera
from local_console.core.camera import MQTTTopics
from local_console.core.config import get_config
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import SetFactoryReset
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.gui.utils.axis_mapping import pixel_roi_from_normals
from local_console.gui.utils.axis_mapping import UnitROI
from local_console.gui.utils.enums import Screen
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.utils.sync_async import SyncAsyncBridge
from local_console.servers.broker import spawn_broker
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.flatbuffers import FlatBuffers
from local_console.utils.fswatch import StorageSizeWatcher
from local_console.utils.local_network import LOCAL_IP
from local_console.utils.timing import TimeoutBehavior
from local_console.utils.tracking import TrackingVariable

logger = logging.getLogger(__name__)


class Driver:
    def __init__(self, gui: type[MDApp]) -> None:
        self.gui = gui

        self.mqtt_client = Agent()
        self.upload_port = 0
        self.temporary_base: Optional[Path] = None
        self.temporary_image_directory: Optional[Path] = None
        self.temporary_inference_directory: Optional[Path] = None
        self.image_directory_config: TrackingVariable[Path] = TrackingVariable()
        self.inference_directory_config: TrackingVariable[Path] = TrackingVariable()
        self.total_dir_watcher = StorageSizeWatcher()
        self.flatbuffers_schema: Optional[Path] = None
        self.config = get_config()

        self.camera_state = Camera()
        self.flatbuffers = FlatBuffers()

        # This takes care of ensuring the device reports its state
        # with bounded periodicity (expect to receive a message within 6 seconds)
        if not self.evp1_mode:
            self.periodic_reports = TimeoutBehavior(6, self.set_periodic_reports)

        # This timeout behavior takes care of updating the connectivity
        # status in case there are no incoming messages from the camera
        # for longer than the threshold
        self.connection_status = TimeoutBehavior(
            Camera.CONNECTION_STATUS_TIMEOUT.seconds, self.connection_status_timeout
        )

        self.start_flags = {
            "mqtt": trio.Event(),
            "webserver": trio.Event(),
        }

        self.bridge = SyncAsyncBridge()

    @property
    def evp1_mode(self) -> bool:
        return self.config.evp.iot_platform.lower() == "evp1"

    @trio.lowlevel.disable_ki_protection
    async def main(self) -> None:
        async with trio.open_nursery() as nursery:
            try:
                nursery.start_soon(self.bridge.bridge_listener)
                nursery.start_soon(self.services_loop)
                await self.gui.async_run(async_lib="trio")
            except KeyboardInterrupt:
                logger.info("Cancelled per user request via keyboard")
            finally:
                self.bridge.close_task_queue()
                nursery.cancel_scope.cancel()

    async def services_loop(self) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.mqtt_setup)
            nursery.start_soon(self.blobs_webserver_task)

    async def mqtt_setup(self) -> None:
        async with (
            trio.open_nursery() as nursery,
            spawn_broker(self.config, nursery, False, "nicebroker"),
            self.mqtt_client.mqtt_scope(
                [
                    MQTTTopics.ATTRIBUTES_REQ.value,
                    MQTTTopics.TELEMETRY.value,
                    MQTTTopics.RPC_RESPONSES.value,
                    MQTTTopics.ATTRIBUTES.value,
                ]
            ),
        ):
            self.start_flags["mqtt"].set()

            assert self.mqtt_client.client  # appease mypy
            self.connection_status.spawn_in(nursery)
            if not self.evp1_mode:
                self.periodic_reports.spawn_in(nursery)

            streaming_stop_required = True
            async with self.mqtt_client.client.messages() as mgen:
                async for msg in mgen:
                    if await check_attributes_request(
                        self.mqtt_client, msg.topic, msg.payload.decode()
                    ):
                        self.camera_state.attributes_available = True
                        # attributes request handshake is performed at (re)connect
                        # when reconnecting, multiple requests might be made
                        if streaming_stop_required:
                            await self.streaming_rpc_stop()
                            streaming_stop_required = False

                    payload = json.loads(msg.payload)
                    self.camera_state.process_incoming(msg.topic, payload)
                    self.update_camera_status()
                    await self.process_factory_reset()

                    if not self.evp1_mode and self.camera_state.is_ready:
                        self.periodic_reports.tap()

                    self.connection_status.tap()

    def from_sync(self, async_fn: Callable, *args: Any) -> None:
        self.bridge.enqueue_task(async_fn, *args)

    async def process_factory_reset(self) -> None:
        if self.camera_state.is_new_device_config and self.camera_state.device_config:
            factory_reset = self.camera_state.device_config.Permission.FactoryReset
            logger.info(f"Factory Reset is {factory_reset}")
            if not factory_reset:
                await self.mqtt_client.configure(
                    "backdoor-EA_Main",
                    "placeholder",
                    SetFactoryReset(
                        Permission=Permission(FactoryReset=True)
                    ).model_dump_json(),
                )

    @run_on_ui_thread
    def update_camera_status(self) -> None:
        self.gui.is_ready = self.camera_state.is_ready
        sensor_state = self.camera_state.sensor_state
        self.gui.is_streaming = self.camera_state.is_streaming
        self.gui.views[Screen.STREAMING_SCREEN].model.stream_status = sensor_state
        self.gui.views[Screen.INFERENCE_SCREEN].model.stream_status = sensor_state
        self.gui.views[
            Screen.APPLICATIONS_SCREEN
        ].model.deploy_status = self.camera_state.deploy_status
        self.gui.views[
            Screen.CONNECTION_SCREEN
        ].model.connected = self.camera_state.connected
        self.gui.views[
            Screen.AI_MODEL_SCREEN
        ].model.device_config = self.camera_state.device_config

    async def blobs_webserver_task(self) -> None:
        """
        Spawn a webserver on an arbitrary available port for receiving
        images from a camera.
        :param on_received: Callback that is triggered for each new received image
        :param base_dir: Path to directory where images will be saved into
        :return:
        """
        with (
            TemporaryDirectory(prefix="LocalConsole_") as tempdir,
            AsyncWebserver(
                Path(tempdir), port=0, on_incoming=self.process_camera_upload
            ) as image_serve,
        ):
            logger.info(f"Uploading data into {tempdir}")

            assert image_serve.port
            self.upload_port = image_serve.port
            logger.info(f"Webserver listening on port {self.upload_port}")
            self.temporary_base = Path(tempdir)
            self.temporary_image_directory = Path(tempdir) / "images"
            self.temporary_inference_directory = Path(tempdir) / "inferences"
            self.temporary_image_directory.mkdir(exist_ok=True)
            self.temporary_inference_directory.mkdir(exist_ok=True)
            self.set_image_directory(self.temporary_image_directory)
            self.set_inference_directory(self.temporary_inference_directory)

            self.start_flags["webserver"].set()
            await trio.sleep_forever()

    def process_camera_upload(self, incoming_file: Path) -> None:
        if incoming_file.parent.name == "images":
            final_file = self.save_into_image_directory(incoming_file)
            self.update_images_display(final_file)
        elif incoming_file.parent.name == "inferences":
            final_file = self.save_into_inferences_directory(incoming_file)
            if self.flatbuffers_schema:
                self.update_inference_data_flatbuffers(final_file)
            else:
                self.update_inference_data(final_file.read_text())
        else:
            logger.warning(f"Unknown incoming file: {incoming_file}")

    def check_and_create_directory(self, directory: Path) -> None:
        if not directory.exists():
            logger.warning(f"{directory} does not exist. Creating directory...")
            directory.mkdir(exist_ok=True)

    @run_on_ui_thread
    def set_image_directory(self, new_dir: Path) -> None:
        self.image_directory_config.value = new_dir
        self.gui.image_dir_path = str(self.image_directory_config.value)
        self.check_and_create_directory(new_dir)
        if self.image_directory_config.previous:
            self.total_dir_watcher.unwatch_path(self.image_directory_config.previous)
        self.total_dir_watcher.set_path(self.image_directory_config.value)

    @run_on_ui_thread
    def set_inference_directory(self, new_dir: Path) -> None:
        self.inference_directory_config.value = new_dir
        self.gui.inference_dir_path = str(self.inference_directory_config.value)
        self.check_and_create_directory(new_dir)
        if self.inference_directory_config.previous:
            self.total_dir_watcher.unwatch_path(
                self.inference_directory_config.previous
            )
        self.total_dir_watcher.set_path(self.inference_directory_config.value)

    @run_on_ui_thread
    def update_images_display(self, incoming_file: Path) -> None:
        self.gui.views[Screen.STREAMING_SCREEN].ids.stream_image.update_image_data(
            incoming_file
        )
        self.gui.views[Screen.INFERENCE_SCREEN].ids.stream_image.update_image_data(
            incoming_file
        )

    @run_on_ui_thread
    def update_inference_data(self, inference_data: str) -> None:
        self.gui.views[
            Screen.INFERENCE_SCREEN
        ].ids.inference_field.text = inference_data

    @run_on_ui_thread
    def update_inference_data_flatbuffers(self, incoming_file: Path) -> None:
        if self.flatbuffers_schema and incoming_file and incoming_file.exists():
            output_name = "SmartCamera"
            assert self.temporary_base  # appease mypy
            if self.flatbuffers.flatbuffer_binary_to_json(
                self.flatbuffers_schema,
                incoming_file,
                output_name,
                self.temporary_base,
            ):
                try:
                    with open(self.temporary_base / f"{output_name}.json") as file:
                        self.gui.views[
                            Screen.INFERENCE_SCREEN
                        ].ids.inference_field.text = file.read()
                except FileNotFoundError:
                    logger.warning(
                        "Error while reading human-readable. Flatbuffers schema might be different from inference data."
                    )
                except Exception as e:
                    logger.warning(f"Unknown error while reading human-readable {e}")

    def save_into_inferences_directory(self, incoming_file: Path) -> Path:
        final = incoming_file
        assert self.inference_directory_config.value  # appease mypy
        self.check_and_create_directory(self.inference_directory_config.value)
        if incoming_file.parent != self.inference_directory_config.value:
            final = Path(
                shutil.move(incoming_file, self.inference_directory_config.value)
            )
        self.total_dir_watcher.incoming(final)
        return final

    def save_into_image_directory(self, incoming_file: Path) -> Path:
        final = incoming_file
        assert self.image_directory_config.value  # appease mypy
        self.check_and_create_directory(self.image_directory_config.value)
        if incoming_file.parent != self.image_directory_config.value:
            final = Path(shutil.move(incoming_file, self.image_directory_config.value))
        self.total_dir_watcher.incoming(final)
        return final

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StartUploadInferenceData"
        upload_url = f"http://{LOCAL_IP}:{self.upload_port}"
        assert self.temporary_image_directory  # appease mypy
        assert self.temporary_inference_directory  # appease mypy

        (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(roi)

        await self.mqtt_client.rpc(
            instance_id,
            method,
            StartUploadInferenceData(
                StorageName=upload_url,
                StorageSubDirectoryPath=self.temporary_image_directory.name,
                StorageNameIR=upload_url,
                StorageSubDirectoryPathIR=self.temporary_inference_directory.name,
                CropHOffset=h_offset,
                CropVOffset=v_offset,
                CropHSize=h_size,
                CropVSize=v_size,
            ).model_dump_json(),
        )

    async def streaming_rpc_stop(self) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StopUploadInferenceData"
        await self.mqtt_client.rpc(instance_id, method, "{}")

    async def set_periodic_reports(self) -> None:
        assert not self.evp1_mode
        # Configure the device to emit status reports twice
        # as often as the timeout expiration, to avoid that
        # random deviations in reporting periodicity make the timer
        # to expire unnecessarily.
        timeout = int(0.5 * self.periodic_reports.timeout_secs)
        await self.mqtt_client.device_configure(
            DesiredDeviceConfig(
                reportStatusIntervalMax=timeout,
                reportStatusIntervalMin=min(timeout, 1),
            )
        )

    async def connection_status_timeout(self) -> None:
        logger.debug("Connection status timed out: camera is disconnected")
        self.update_camera_status()
