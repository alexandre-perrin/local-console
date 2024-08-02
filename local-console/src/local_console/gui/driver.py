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
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import Optional

import trio
from kivymd.app import MDApp
from local_console.clients.agent import Agent
from local_console.clients.agent import check_attributes_request
from local_console.core.camera.axis_mapping import pixel_roi_from_normals
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import get_output_from_inference_results
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import get_config
from local_console.core.config import get_device_configs
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import SetFactoryReset
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.gui.device_manager import DeviceManager
from local_console.gui.drawer.classification import ClassificationDrawer
from local_console.gui.drawer.objectdetection import DetectionDrawer
from local_console.gui.enums import ApplicationConfiguration
from local_console.gui.enums import ApplicationType
from local_console.gui.utils.enums import Screen
from local_console.gui.utils.sync_async import AsyncFunc
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.utils.sync_async import SyncAsyncBridge
from local_console.servers.broker import spawn_broker
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.timing import TimeoutBehavior


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
        self.latest_image_file: Optional[Path] = None
        # Used to identify if output tensors are missing
        self.consecutives_images = 0
        self.send_channel: trio.MemorySendChannel[MessageType] | None = None
        self.receive_channel: trio.MemoryReceiveChannel[MessageType] | None = None

        self.device_manager: Optional[DeviceManager] = None
        self.camera_state: Optional[CameraState] = None

        # This takes care of ensuring the device reports its state
        # with bounded periodicity (expect to receive a message within 6 seconds)
        if not self.evp1_mode:
            self.periodic_reports = TimeoutBehavior(6, self.set_periodic_reports)

        # This timeout behavior takes care of updating the connectivity
        # status in case there are no incoming messages from the camera
        # for longer than the threshold

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
                nursery.start_soon(self.mqtt_setup)
                nursery.start_soon(self.blobs_webserver_task)
                self.send_channel, self.receive_channel = trio.open_memory_channel(0)
                self.camera_state = CameraState(
                    self.send_channel, nursery, trio.lowlevel.current_trio_token()
                )
                assert self.camera_state is not None
                self.camera_state.device_config.subscribe_async(
                    self.process_factory_reset
                )
                self.camera_state.initialize_connection_variables(self.config)

                self.device_manager = DeviceManager(
                    self.send_channel, nursery, trio.lowlevel.current_trio_token()
                )
                self.device_manager.start_previous_devices(get_device_configs())
                if self.device_manager.active_device is not None:
                    self.gui.switch_proxy()

                await self.gui.async_run(async_lib="trio")
            except KeyboardInterrupt:
                logger.info("Cancelled per user request via keyboard")
            finally:
                self.bridge.close_task_queue()
                nursery.cancel_scope.cancel()

    async def mqtt_setup(self) -> None:
        async with (
            trio.open_nursery() as nursery,
            spawn_broker(self.config, nursery, False),
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
            if not self.evp1_mode:
                self.periodic_reports.spawn_in(nursery)
            assert self.camera_state is not None

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

                    if not self.evp1_mode and self.camera_state.is_ready:
                        self.periodic_reports.tap()

    def from_sync(self, async_fn: AsyncFunc, *args: Any) -> None:
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

            assert self.camera_state

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
        assert self.camera_state

        if incoming_file.parent.name == "inferences":
            target_dir = self.camera_state.inference_dir_path.value
            assert target_dir
            final_file = self.save_into_input_directory(incoming_file, target_dir)
            output_data = get_output_from_inference_results(final_file.read_bytes())

            payload_render = final_file.read_text()
            if self.camera_state.vapp_schema_file.value:
                try:
                    output_tensor = self.get_flatbuffers_inference_data(output_data)
                    if output_tensor:
                        payload_render = json.dumps(output_tensor, indent=2)
                        output_data = output_tensor  # type: ignore
                except FlatbufferError as e:
                    logger.error("Error decoding inference data:", exc_info=e)
            self.update_inference_data(payload_render)

            # assumes input and output tensor received in that order
            assert self.latest_image_file
            try:
                {
                    ApplicationType.CLASSIFICATION.value: ClassificationDrawer,
                    ApplicationType.DETECTION.value: DetectionDrawer,
                }[str(self.camera_state.vapp_type.value)].process_frame(
                    self.latest_image_file, output_data
                )
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

    async def show_messages(self) -> None:
        assert self.receive_channel
        async for value in self.receive_channel:
            self.show_message_gui(value)

    @run_on_ui_thread
    def show_message_gui(self, msg: MessageType) -> None:
        type_ = msg[0]
        if type_ == "error":
            self.gui.display_error(msg[1], 30)

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

    def get_flatbuffers_inference_data(
        self, flatbuffer_payload: bytes
    ) -> None | str | dict:
        return_value = None
        assert self.camera_state
        if self.camera_state.vapp_schema_file.value:
            json_data = flatbuffer_binary_to_json(
                self.camera_state.vapp_schema_file.value, flatbuffer_payload
            )
            labels_map = self.camera_state.vapp_labels_map.value
            if labels_map:
                add_class_names(json_data, labels_map)
            return_value = json_data

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
        assert self.camera_state
        self.camera_state.total_dir_watcher.incoming(final)
        return final

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StartUploadInferenceData"
        host = get_my_ip_by_routing()
        upload_url = f"http://{host}:{self.upload_port}"
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

    async def send_app_config(self, config: str) -> None:
        await self.mqtt_client.configure(
            ApplicationConfiguration.NAME,
            ApplicationConfiguration.CONFIG_TOPIC,
            config,
        )

    def do_app_deployment(self) -> None:
        assert self.camera_state
        task = partial(self.camera_state.do_app_deployment, self.mqtt_client)
        self.from_sync(task)
