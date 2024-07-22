# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
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
from local_console.core.camera import CameraState
from local_console.core.camera import FirmwareExtension
from local_console.core.camera import MQTTTopics
from local_console.core.camera import OTAUpdateModule
from local_console.core.camera import StreamStatus
from local_console.core.camera.axis_mapping import pixel_roi_from_normals
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.config import get_config
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import SetFactoryReset
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.gui.drawer.objectdetection import process_frame
from local_console.gui.enums import ApplicationConfiguration
from local_console.gui.utils.enums import Screen
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.utils.sync_async import SyncAsyncBridge
from local_console.servers.broker import spawn_broker
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.flatbuffers import FlatBuffers
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import DirectoryMonitor
from local_console.utils.fstools import StorageSizeWatcher
from local_console.utils.local_network import LOCAL_IP
from local_console.utils.timing import TimeoutBehavior
from local_console.utils.validation import validate_imx500_model_file

logger = logging.getLogger(__name__)


class Driver:
    def __init__(self, gui: type[MDApp]) -> None:
        self.gui = gui

        self.config = get_config()
        self.mqtt_client = Agent(self.config)
        self.upload_port = 0
        self.temporary_base: Optional[Path] = None
        self.temporary_image_directory: Optional[Path] = None
        self.temporary_inference_directory: Optional[Path] = None
        self.total_dir_watcher = StorageSizeWatcher()
        self.class_id_to_name: Optional[dict] = None
        self.latest_image_file: Optional[Path] = None
        # Used to identify if output tensors are missing
        self.consecutives_images = 0

        self.camera_state = CameraState()
        self.camera_state.device_config.subscribe_async(self.process_factory_reset)
        self.flatbuffers = FlatBuffers()

        # This takes care of ensuring the device reports its state
        # with bounded periodicity (expect to receive a message within 6 seconds)
        if not self.evp1_mode:
            self.periodic_reports = TimeoutBehavior(6, self.set_periodic_reports)

        # This timeout behavior takes care of updating the connectivity
        # status in case there are no incoming messages from the camera
        # for longer than the threshold
        self.connection_status = TimeoutBehavior(
            CameraState.CONNECTION_STATUS_TIMEOUT.seconds,
            self.connection_status_timeout,
        )

        self.start_flags = {
            "mqtt": trio.Event(),
            "webserver": trio.Event(),
        }
        self.bridge = SyncAsyncBridge()
        self.dir_monitor = DirectoryMonitor()

        self._init_core_variables()
        self._init_ai_model_functions()
        self._init_firmware_file_functions()
        self._init_input_directories()
        self._init_stream_variables()
        self._init_vapp_file_functions()

    def _init_core_variables(self) -> None:
        self.gui.mdl.bind_state_to_proxy("is_ready", self.camera_state)
        self.gui.mdl.bind_state_to_proxy("is_streaming", self.camera_state)
        self.gui.mdl.bind_state_to_proxy("device_config", self.camera_state)

    def _init_stream_variables(self) -> None:
        # Proxy->State because we want the user to set this value via the GUI
        self.gui.mdl.bind_proxy_to_state("roi", self.camera_state)

        # State->Proxy because this is either read from the device state
        # or from states computed within the GUI code
        self.gui.mdl.bind_state_to_proxy("stream_status", self.camera_state)

    def _init_ai_model_functions(self) -> None:
        # Proxy->State because we want the user to set this value via the GUI
        self.gui.mdl.bind_proxy_to_state("ai_model_file", self.camera_state, Path)

        # State->Proxy because this is computed from the model file
        self.gui.mdl.bind_state_to_proxy("ai_model_file_valid", self.camera_state)

        def validate_file(current: Optional[Path], previous: Optional[Path]) -> None:
            if current:
                self.camera_state.ai_model_file_valid.value = (
                    validate_imx500_model_file(current)
                )

        self.camera_state.ai_model_file.subscribe(validate_file)

    def _init_firmware_file_functions(self) -> None:
        # Proxy->State because we want the user to set these values via the GUI
        self.gui.mdl.bind_proxy_to_state("firmware_file", self.camera_state, Path)
        self.gui.mdl.bind_proxy_to_state("firmware_file_version", self.camera_state)
        self.gui.mdl.bind_proxy_to_state("firmware_file_type", self.camera_state)
        # Default value that matches the default widget selection
        self.gui.mdl.firmware_file_type = OTAUpdateModule.APFW

        # State->Proxy because these are computed from the firmware_file
        self.gui.mdl.bind_state_to_proxy("firmware_file_valid", self.camera_state)
        self.gui.mdl.bind_state_to_proxy("firmware_file_hash", self.camera_state)

        def validate_file(current: Optional[Path], previous: Optional[Path]) -> None:
            if current:
                is_valid = True
                if self.camera_state.firmware_file_type.value == OTAUpdateModule.APFW:
                    if current.suffix != FirmwareExtension.APPLICATION_FW:
                        is_valid = False
                else:
                    if current.suffix != FirmwareExtension.SENSOR_FW:
                        is_valid = False

                self.camera_state.firmware_file_hash.value = (
                    get_package_hash(current) if is_valid else ""
                )
                self.camera_state.firmware_file_valid.value = is_valid

        self.camera_state.firmware_file.subscribe(validate_file)

    def _init_input_directories(self) -> None:
        self.gui.mdl.bind_state_to_proxy("image_dir_path", self.camera_state, str)
        self.camera_state.image_dir_path.subscribe(self.input_directory_setup)
        self.gui.mdl.bind_state_to_proxy("inference_dir_path", self.camera_state, str)
        self.camera_state.inference_dir_path.subscribe(self.input_directory_setup)

    def _init_vapp_file_functions(self) -> None:
        self.gui.mdl.bind_proxy_to_state("vapp_config_file", self.camera_state)
        self.gui.mdl.bind_proxy_to_state("vapp_labels_file", self.camera_state)
        self.gui.mdl.bind_proxy_to_state("vapp_type", self.camera_state)
        """
        `vapp_schema_file` is not bound because it is important that the chosen
        file undergoes thorough validation before being committed.
        """

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
                        self.camera_state.attributes_available.value = True
                        # attributes request handshake is performed at (re)connect
                        # when reconnecting, multiple requests might be made
                        if streaming_stop_required:
                            await self.streaming_rpc_stop()
                            streaming_stop_required = False

                    payload = json.loads(msg.payload)
                    await self.camera_state.process_incoming(msg.topic, payload)
                    self.update_camera_status()

                    if not self.evp1_mode and self.camera_state.is_ready:
                        self.periodic_reports.tap()

                    self.connection_status.tap()

    def from_sync(self, async_fn: Callable, *args: Any) -> None:
        self.bridge.enqueue_task(async_fn, *args)

    async def process_factory_reset(
        self,
        current: Optional[DeviceConfiguration],
        previous: Optional[DeviceConfiguration],
    ) -> None:
        assert current
        assert self.mqtt_client

        factory_reset = current.Permission.FactoryReset
        logger.debug(f"Factory Reset is {factory_reset}")
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
        stream_status = self.camera_state.stream_status
        self.gui.views[Screen.STREAMING_SCREEN].model.stream_status = stream_status
        self.gui.views[Screen.INFERENCE_SCREEN].model.stream_status = stream_status
        self.gui.views[Screen.APPLICATIONS_SCREEN].model.deploy_status = (
            self.camera_state.deploy_status
        )
        self.gui.views[Screen.CONNECTION_SCREEN].model.connected = (
            self.camera_state.connected
        )

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
            self.camera_state.image_dir_path.value = self.temporary_image_directory
            self.camera_state.inference_dir_path.value = (
                self.temporary_inference_directory
            )

            self.start_flags["webserver"].set()
            await trio.sleep_forever()

    def process_camera_upload(self, incoming_file: Path) -> None:
        if incoming_file.parent.name == "inferences":
            target_dir = self.camera_state.inference_dir_path.value
            assert target_dir
            final_file = self.save_into_input_directory(incoming_file, target_dir)
            output_data = self.flatbuffers.get_output_from_inference_results(final_file)
            if self.camera_state.vapp_schema_file.value:
                output_tensor = self.get_flatbuffers_inference_data(output_data)
                if output_tensor:
                    self.update_inference_data(json.dumps(output_tensor, indent=2))
                    output_data = output_tensor  # type: ignore
            else:
                self.update_inference_data(final_file.read_text())

            # assumes input and output tensor received in that order
            assert self.latest_image_file
            try:
                process_frame(self.latest_image_file, output_data)
            except Exception as e:
                logger.error(f"Error while performing the drawing: {e}")
            self.update_images_display(self.latest_image_file)
            self.consecutives_images = 0

        elif incoming_file.parent.name == "images":
            target_dir = self.camera_state.image_dir_path.value
            assert target_dir
            final_file = self.save_into_input_directory(incoming_file, target_dir)
            self.latest_image_file = final_file
            if self.consecutives_images > 0:
                self.update_images_display(final_file)
            self.consecutives_images += 1
        else:
            logger.warning(f"Unknown incoming file: {incoming_file}")

    def input_directory_setup(
        self, current: Optional[Path], previous: Optional[Path]
    ) -> None:
        assert current

        check_and_create_directory(current)
        if previous:
            self.total_dir_watcher.unwatch_path(previous)
        self.total_dir_watcher.set_path(current)

        self.dir_monitor.watch(current, self.notify_directory_deleted)
        if previous:
            self.dir_monitor.unwatch(previous)

    @run_on_ui_thread
    def notify_directory_deleted(self, directory: Path) -> None:
        self.gui.display_error(str(directory), "has been unexpectedly removed", 30)

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
        self.gui.views[Screen.INFERENCE_SCREEN].ids.inference_field.text = (
            inference_data
        )

    def get_flatbuffers_inference_data(self, output: bytes) -> None | str | dict:
        if self.camera_state.vapp_schema_file.value:
            output_name = "SmartCamera"
            assert self.temporary_base  # appease mypy
            return_value = None
            if self.flatbuffers.flatbuffer_binary_to_json(
                self.camera_state.vapp_schema_file.value,
                output,
                output_name,
                self.temporary_base,
            ):
                try:
                    return_value = None
                    with open(self.temporary_base / f"{output_name}.json") as file:
                        json_data = json.load(file)
                        if self.class_id_to_name:
                            add_class_names(json_data, self.class_id_to_name)

                        return_value = json_data
                except FileNotFoundError:
                    logger.warning(
                        "Error while reading human-readable. Flatbuffers schema might be different from inference data."
                    )
                except Exception as e:
                    logger.warning(f"Unknown error while reading human-readable {e}")
        return return_value

    def save_into_input_directory(self, incoming_file: Path, target_dir: Path) -> Path:
        assert incoming_file.is_file()

        """
        The following cannot be asserted in the current implementation
        based on temporary directories, because of unexpected OS deletion
        of the target directory if it hasn't been set to the default
        temporary directory.
        """
        # assert target_dir.is_dir()

        final = incoming_file
        check_and_create_directory(final.parent)
        if incoming_file.parent != target_dir:
            check_and_create_directory(target_dir)
            final = Path(shutil.move(incoming_file, target_dir))

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
        self.camera_state.stream_status.value = StreamStatus.Inactive
        self.update_camera_status()

    async def send_app_config(self, config: str) -> None:
        await self.mqtt_client.configure(
            ApplicationConfiguration.NAME,
            ApplicationConfiguration.CONFIG_TOPIC,
            config,
        )
