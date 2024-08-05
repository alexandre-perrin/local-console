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
from functools import partial
from pathlib import Path
from typing import Any
from typing import Optional

import trio
from kivymd.app import MDApp
from local_console.clients.agent import Agent
from local_console.clients.agent import check_attributes_request
from local_console.core.camera.axis_mapping import pixel_roi_from_normals
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import get_config
from local_console.core.config import get_device_configs
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import SetFactoryReset
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.device_manager import DeviceManager
from local_console.gui.enums import ApplicationConfiguration
from local_console.gui.utils.sync_async import AsyncFunc
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.utils.sync_async import SyncAsyncBridge
from local_console.servers.broker import spawn_broker
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.timing import TimeoutBehavior


logger = logging.getLogger(__name__)


class Driver:
    DEFAULT_DEVICE_NAME = "Default"
    DEFAULT_DEVICE_PORT = 1883

    def __init__(self, gui: type[MDApp]) -> None:
        self.gui = gui
        self.config = get_config()
        self.send_channel: trio.MemorySendChannel[MessageType] | None = None
        self.receive_channel: trio.MemoryReceiveChannel[MessageType] | None = None

        self.device_manager: Optional[DeviceManager] = None
        self.camera_state: Optional[CameraState] = None

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
                self.device_manager.init_devices(get_device_configs())
                if self.device_manager.active_device is not None:
                    self.gui.switch_proxy()

                self._init_devices()

                await self.gui.async_run(async_lib="trio")
            except KeyboardInterrupt:
                logger.info("Cancelled per user request via keyboard")
            finally:
                self.bridge.close_task_queue()
                nursery.cancel_scope.cancel()

    def _init_devices(self) -> None:
        """
        Initialize default devices if none exist in the configuration.

        This method checks if there are any devices currently configured in the
        device manager. If no devices are found, it creates a default device
        using the predefined default name and port. The default device is then
        added to the device manager, set as the active device, and the GUI proxy
        is switched to reflect this change.
        """
        assert self.device_manager
        if self.device_manager.num_devices == 0:
            # At least 1 device
            default_device = DeviceListItem(
                name=self.DEFAULT_DEVICE_NAME, port=str(self.DEFAULT_DEVICE_PORT)
            )
            self.device_manager.add_device(default_device)
            self.device_manager.set_active_device(default_device.name)
            self.gui.switch_proxy()

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

                    self.camera_state.update_connection_status()

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

    async def show_messages(self) -> None:
        assert self.receive_channel
        async for value in self.receive_channel:
            self.show_message_gui(value)

    @run_on_ui_thread
    def show_message_gui(self, msg: MessageType) -> None:
        type_ = msg[0]
        if type_ == "error":
            self.gui.display_error(msg[1], 30)

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StartUploadInferenceData"
        host = get_my_ip_by_routing()
        assert self.camera_state
        upload_url = f"http://{host}:{self.camera_state.upload_port}"
        assert self.camera_state.image_dir_path.value  # appease mypy
        assert self.camera_state.inference_dir_path.value  # appease mypy

        (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(roi)

        await self.mqtt_client.rpc(
            instance_id,
            method,
            StartUploadInferenceData(
                StorageName=upload_url,
                StorageSubDirectoryPath=Path(
                    self.camera_state.image_dir_path.value
                ).name,
                StorageNameIR=upload_url,
                StorageSubDirectoryPathIR=Path(
                    self.camera_state.inference_dir_path.value
                ).name,
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
