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
from functools import partial
from typing import Any

import trio
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceConnection
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

    def init_devices(self, device_configs: list[DeviceConnection]) -> None:
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
            return

        for device in device_configs:
            self.add_device_to_internals(device)
            self.initialize_persistency(device.name)

            self.set_active_device(config_obj.get_active_device_config().name)

    @property
    def num_devices(self) -> int:
        n = len(self.state_factory)
        assert n == len(self.proxies_factory)
        return n

    def add_device_to_internals(self, device: DeviceConnection) -> None:
        proxy = CameraStateProxy()
        state = CameraState(self.send_channel.clone(), self.nursery, self.trio_token)
        self.proxies_factory[device.name] = proxy
        self.state_factory[device.name] = state

        self.bind_state_proxy(proxy, state)

        config = config_obj.get_config()
        device.mqtt.port = int(device.mqtt.port)
        state.initialize_connection_variables(config.evp.iot_platform, device)
        self.initialize_persistency(device.name)
        state.finish_setup()

    def add_device(self, device: DeviceListItem) -> None:
        device_connection = config_obj.add_device(device)
        config_obj.save_config()
        self.add_device_to_internals(device_connection)

    def remove_device(self, name: str) -> None:
        config_obj.remove_device(name)
        config_obj.save_config()
        del self.proxies_factory[name]
        del self.state_factory[name]

    def get_active_device_proxy(self) -> CameraStateProxy:
        assert self.active_device
        return self.proxies_factory[self.active_device.name]

    def get_active_device_state(self) -> CameraState:
        assert self.active_device
        return self.state_factory[self.active_device.name]

    def get_device_configs(self) -> list[DeviceConnection]:
        return config_obj.get_device_configs()

    def set_active_device(self, name: str) -> None:
        """
        This is the function to set active device.
        To be implemented for handling multiple devices.
        """
        config_obj.config.active_device = name
        for device in config_obj.config.devices:
            if device.name == name:
                self.active_device = DeviceListItem(
                    name=name, port=str(device.mqtt.port)
                )
                return
        raise Exception("Device not found")

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

    def _register_persistency(self, device_name: str) -> None:
        def save_configuration(attribute: str, current: Any, previous: Any) -> None:
            persist = config_obj.get_device_config(device_name).persist
            if attribute == "module_file":
                persist.module_file = current
            if attribute == "ai_model_file":
                persist.ai_model_file = current
                persist.ai_model_file_valid = self.proxies_factory[
                    device_name
                ].ai_model_file_valid
            config_obj.save_config()

        # List of attributes that trigger persistency
        # TODO: remove str and rely in variable or enum
        self.state_factory[device_name].module_file.subscribe(
            partial(save_configuration, "module_file")
        )
        self.state_factory[device_name].ai_model_file.subscribe(
            partial(save_configuration, "ai_model_file")
        )

    def _update_from_persistency(self, device_name: str) -> None:
        # Update attributes from persistent configuration
        persist = config_obj.get_device_config(device_name).persist
        assert persist
        if persist.module_file:
            self.proxies_factory[device_name].module_file = persist.module_file
        if persist.ai_model_file:
            self.proxies_factory[device_name].ai_model_file = persist.ai_model_file
            self.proxies_factory[device_name].ai_model_file_valid = (
                persist.ai_model_file_valid
            )

    def initialize_persistency(self, device_name: str) -> None:
        self._update_from_persistency(device_name)
        self._register_persistency(device_name)
