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
import logging

import trio
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import add_device_to_config
from local_console.core.config import get_config
from local_console.core.config import get_device_configs
from local_console.core.config import remove_device_config
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.model.camera_proxy import CameraStateProxy

logger = logging.getLogger(__name__)


class DeviceManager:

    DEFAULT_DEVICE_NAME = "Default"
    DEFAULT_DEVICE_PORT = 1883

    def __init__(
        self,
        send_channel: trio.MemorySendChannel[MessageType],
        nursery: trio.Nursery,
        trio_token: trio.lowlevel.TrioToken,
    ) -> None:
        self.send_channel = send_channel
        self.nursery = nursery
        self.trio_token = trio_token

        self.active_device: DeviceListItem | None = None
        self.proxies_factory: dict[str, CameraStateProxy] = {}
        self.state_factory: dict[str, CameraState] = {}

    def init_devices(self, device_configs: list[DeviceListItem]) -> None:
        """
        Initializes the devices based on the provided configuration list.
        If no devices are found, it creates a default device
        using the predefined default name and port. The default device is then
        added to the device manager, set as the active device, and the GUI proxy
        is switched to reflect this change.
        """
        if len(device_configs) == 0:
            # There should be at least one device
            default_device = DeviceListItem(
                name=self.DEFAULT_DEVICE_NAME, port=str(self.DEFAULT_DEVICE_PORT)
            )
            self.add_device(default_device)
            self.set_active_device(default_device.name)

        for device in device_configs:
            if not self.active_device:
                self.active_device = device
            self.add_device_to_internals(device)

    @property
    def num_devices(self) -> int:
        n = len(self.state_factory)
        assert n == len(self.proxies_factory)
        return n

    def add_device_to_internals(self, device: DeviceListItem) -> None:
        proxy = CameraStateProxy()
        state = CameraState(self.send_channel.clone(), self.nursery, self.trio_token)
        self.bind_state_proxy(proxy, state)

        config = get_config()
        config.mqtt.port = int(device.port)
        state.initialize_connection_variables(config)
        state.initialize_persistency(device.name)
        state.finish_setup()

        self.proxies_factory[device.name] = proxy
        self.state_factory[device.name] = state

    def add_device(self, device: DeviceListItem) -> None:
        add_device_to_config(device)
        self.add_device_to_internals(device)

    def remove_device(self, name: str) -> None:
        remove_device_config(name)
        del self.proxies_factory[name]
        del self.state_factory[name]

    def get_device_configs(self) -> list[DeviceListItem]:
        return get_device_configs()

    def get_active_device_proxy(self) -> CameraStateProxy:
        assert self.active_device
        return self.proxies_factory[self.active_device.name]

    def get_active_device_state(self) -> CameraState:
        assert self.active_device
        return self.state_factory[self.active_device.name]

    def set_active_device(self, name: str) -> None:
        self.active_device = next(
            filter(lambda device: device.name == name, get_device_configs())
        )

    def bind_state_proxy(
        self, proxy: CameraStateProxy, camera_state: CameraState
    ) -> None:
        proxy.bind_core_variables(camera_state)
        proxy.bind_stream_variables(camera_state)
        proxy.bind_connections(camera_state)
        proxy.bind_ai_model_function(camera_state)
        proxy.bind_firmware_file_functions(camera_state)
        proxy.bind_input_directories(camera_state)
        proxy.bind_vapp_file_functions(camera_state)
        proxy.bind_app_module_functions(camera_state)
        proxy.bind_streaming_and_inference(camera_state)
