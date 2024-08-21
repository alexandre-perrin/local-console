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
from typing import Callable
from typing import Optional

import trio
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.model.camera_proxy import CameraStateProxy

logger = logging.getLogger(__name__)


class DeviceHandlingError(Exception):
    """
    Exception type for device life cycle operations
    """


class DeviceManager:

    DEFAULT_DEVICE_NAME = "Default"
    DEFAULT_DEVICE_PORT = 1883
    _PROXY_TO_STATE_PROPS = [
        "module_file",
        "ai_model_file",
        "size",
        "unit",
        "vapp_type",
        "vapp_schema_file",
        "vapp_config_file",
        "vapp_labels_file",
    ]
    _STATE_TO_PROXY_PROPS = [
        "image_dir_path",
        "inference_dir_path",
    ]

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
        self.proxies_factory: dict[int, CameraStateProxy] = {}
        self.state_factory: dict[int, CameraState] = {}

    async def init_devices(self, device_configs: list[DeviceConnection]) -> None:
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
                name=self.DEFAULT_DEVICE_NAME, port=self.DEFAULT_DEVICE_PORT
            )
            await self.add_device(default_device)
            self.set_active_device(default_device.port)
            return

        for device_conn in device_configs:
            device = DeviceListItem(name=device_conn.name, port=device_conn.mqtt.port)
            await self.add_device(device)

        self.set_active_device(config_obj.get_active_device_config().mqtt.port)

    @property
    def num_devices(self) -> int:
        n = len(self.state_factory)
        assert n == len(self.proxies_factory)
        return n

    async def add_device(
        self,
        device_item: DeviceListItem,
        continuation: Optional[Callable[[DeviceListItem], None]] = None,
    ) -> None:
        """
        Creates the objects that represent a camera device's state in the
        logic, initializing the state and if successful, creates an entry
        for the device in the persistent configuration, sets it up for
        value updates, and finally executes a continuation callback, if
        provided.

        The 'continuation' callback is synchronous, and it is mostly intended
        for scheduling actions in the Kivy thread, such as creating or
        updating widgets on a screen.
        """
        key = device_item.port

        state = CameraState(self.send_channel.clone(), self.trio_token)
        proxy = CameraStateProxy()

        config = config_obj.get_config()
        conn = config_obj.construct_device_record(device_item)
        self.bind_state_proxy(proxy, state)
        state.initialize_connection_variables(config.evp.iot_platform, conn)
        if await self.nursery.start(state.startup):
            config_obj.commit_device_record(conn)
            config_obj.save_config()
            self.state_factory[key] = state
            self.proxies_factory[key] = proxy
            self.initialize_persistency(key)
            if continuation:
                continuation(device_item)

    def rename_device(self, key: int, new_name: str) -> None:
        config_obj.rename_entry(key, new_name)

    def remove_device(self, key: int) -> None:
        if len(self.proxies_factory.keys()) == 1:
            raise DeviceHandlingError("Cannot empty device entry list!")

        if key not in self.state_factory:
            return

        self.state_factory[key].shutdown()
        config_obj.remove_device(key)
        config_obj.save_config()
        del self.proxies_factory[key]
        del self.state_factory[key]
        assert self.active_device
        if key == self.active_device.port:
            new_active_device = self.get_device_configs()[0].mqtt.port
            logger.debug(f"Update active device to {new_active_device}")
            self.set_active_device(new_active_device)

    def get_active_device_proxy(self) -> CameraStateProxy:
        assert self.active_device
        return self.proxies_factory[self.active_device.port]

    def get_active_device_state(self) -> CameraState:
        assert self.active_device
        return self.state_factory[self.active_device.port]

    def get_device_configs(self) -> list[DeviceConnection]:
        return config_obj.get_device_configs()

    def set_active_device(self, key: int) -> None:
        """
        Set the active device if it is already in the device listing
        """
        for device in config_obj.config.devices:
            if device.mqtt.port == key:
                self.active_device = DeviceListItem(
                    name=device.name, port=device.mqtt.port
                )
                config_obj.config.active_device = key
                config_obj.save_config()
                return
        raise DeviceHandlingError(f"Device for port {key} not found")

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

    def _register_persistency(self, key: int) -> None:
        """
        Registers persistency for state attributes of a device. When the state
        attributes change, their new values are saved to the persistent configuration.
        """

        def save_configuration(attribute: str, current: Any, previous: Any) -> None:
            persist = config_obj.get_device_config(key).persist
            for item in self._PROXY_TO_STATE_PROPS + self._STATE_TO_PROXY_PROPS:
                if attribute == item:
                    setattr(persist, item, str(current))

            # Save to disk
            config_obj.save_config()

        # Save configuration for any modification of relevant variables
        for item in self._PROXY_TO_STATE_PROPS + self._STATE_TO_PROXY_PROPS:
            getattr(self.state_factory[key], item).subscribe(
                partial(save_configuration, item)
            )

    def _update_from_persistency(self, key: int) -> None:
        """
        Update attributes of the device's state and proxies from persistent configuration.
        """
        persist = config_obj.get_device_config(key).persist
        assert persist

        # Attributes with `bind_state_to_proxy` requires to update using `.value` to trigger the binding
        for item in self._STATE_TO_PROXY_PROPS:
            if getattr(persist, item):
                setattr(
                    getattr(self.state_factory[key], item),
                    "value",
                    getattr(persist, item),
                )
        # Update using `bind_proxy_to_state`
        for item in self._PROXY_TO_STATE_PROPS:
            if getattr(persist, item):
                setattr(self.proxies_factory[key], item, getattr(persist, item))

    def initialize_persistency(self, key: int) -> None:
        self._register_persistency(key)
        self._update_from_persistency(key)
