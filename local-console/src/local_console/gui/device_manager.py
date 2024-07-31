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

from local_console.core.config import add_device_to_config
from local_console.core.config import get_device_configs
from local_console.core.config import remove_device_config
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.core.camera.state import CameraState
from local_console.clients.agent import Agent
from local_console.core.config import get_config
from local_console.utils.bindings import bind_connections
from local_console.utils.bindings import bind_core_variables
from local_console.utils.bindings import bind_stream_variables
from local_console.utils.bindings import bind_ai_model_function
from local_console.utils.bindings import bind_firmware_file_functions
from local_console.utils.bindings import bind_input_directories
from local_console.utils.bindings import bind_vapp_file_functions
from local_console.utils.bindings import bind_app_module_functions

logger = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self):
        self.active_device: DeviceListItem = None
        self.proxies_factory: dict[str,CameraStateProxy] = {}
        self.state_factory: dict[str,CameraState] = {}
        self.agent_factory: dict[str,Agent] = {}
        self.num_devices = len(get_device_configs())
        for device in get_device_configs():
            self.add_device_to_internals(device)
            if self.num_devices==1:
                self.active_device = device        

    def add_device_to_internals(self, device:DeviceListItem):
        self.proxies_factory[device.name] = CameraStateProxy()
        self.agent_factory[device.name] = Agent(get_config())
        self.state_factory[device.name] = CameraState()
        self.bind_state_proxy(self.proxies_factory[device.name], self.state_factory[device.name])
        config:AgentConfiguration = get_config()
        config.mqtt.port = int(device.port)
        self.state_factory[device.name].initialize_connection_variables(config)

    def add_device(self, device: DeviceListItem) -> None:
        add_device_to_config(device)
        self.add_device_to_internals(device)
        self.num_devices+=1

    def remove_device(self, name: str) -> None:
        remove_device_config(name)
        del self.proxies_factory[name]
        del self.state_factory[name]
        del self.agent_factory[name]
        self.num_devices-=1

    def get_device_config(self) -> list[DeviceListItem]:
        device_configs = get_device_configs()
        return device_configs

    def get_active_device_proxy(self) -> CameraStateProxy:
        return self.proxies_factory[self.active_device.name]

    def get_active_device_state(self) -> CameraState:
        return self.state_factory[self.active_device.name]
    
    def get_active_mqtt_client(self) -> Agent:
        return self.agent_factory[self.active_device.name]
    
    def set_active_device(self, name: str) -> None:
        """
        This is the function to set active device.
        To be implemented for handling multiple devices.
        """
        self.active_device = next(filter(lambda device: device.name == name, get_device_configs()))
    
    def bind_state_proxy(self, proxy: CameraStateProxy, camera_state: CameraState):
        bind_core_variables(proxy, camera_state)
        bind_stream_variables(proxy, camera_state)
        bind_connections(proxy, camera_state)
        bind_ai_model_function(proxy, camera_state)
        bind_firmware_file_functions(proxy, camera_state)
        bind_input_directories(proxy, camera_state)
        bind_vapp_file_functions(proxy, camera_state)
        bind_app_module_functions(proxy, camera_state)
