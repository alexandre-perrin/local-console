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
import re

from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.devices_screen import DevicesScreenModel
from local_console.gui.view.common.components import DeviceItem
from local_console.gui.view.devices_screen.devices_screen import DevicesScreenView

logger = logging.getLogger(__name__)


class DevicesScreenController(BaseController):
    """
    The `DevicesScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    MAX_NAME_LEN = int(15)
    MAX_PORT_LEN = int(5)
    MAX_DEVICES_LEN = int(5)

    def __init__(self, model: DevicesScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = DevicesScreenView(controller=self, model=self.model)
        assert self.driver.device_manager

        self.restore_device_list(self.driver.device_manager.get_device_configs())

    def get_view(self) -> DevicesScreenView:
        return self.view

    def restore_device_list(self, device_config: list[DeviceListItem]) -> None:
        """
        This function is called on init to restore device list from configuration.
        """
        for device in device_config:
            name = device.name
            port = device.port
            self.add_device_to_device_list(DeviceItem(name=name, port=port))

    def add_device_to_device_list(self, device: DeviceItem) -> None:
        self.view.ids.box_device_list.add_widget(device)

    def set_new_device_name(self, name: str) -> None:
        """
        This function is called when the "Create" button is clicked.
        """
        name = re.sub(r"[^A-Za-z0-9\-_.]", "", name)
        self.view.ids.txt_new_device_name.text = name[: self.MAX_NAME_LEN]

    def set_new_device_port(self, port: str) -> None:
        """
        This function is called when user inputs port.
        """
        port = re.sub(r"\D", "", port)[: self.MAX_PORT_LEN]
        if not port:
            self.set_device_port_text("")
            return
        if port.startswith("0"):
            self.set_device_port_text("0")
            return
        if int(port) > 65535:
            port = port[: self.MAX_PORT_LEN - 1]
        self.set_device_port_text(port)

    def set_device_port_text(self, port: str) -> None:
        self.view.ids.txt_new_device_port.text = port

    def add_new_device(self) -> None:
        """
        This function is called when user inputs name.
        """
        name = self.view.ids.txt_new_device_name.text
        port = self.view.ids.txt_new_device_port.text
        device_list = self.view.ids.box_device_list.children

        if not self.validate_new_device(name, port, device_list):
            return

        # Add the device to the view
        self.add_device_to_device_list(DeviceItem(name=name, port=port))

        assert self.driver.device_manager

        # Save device list into device configuration
        self.driver.device_manager.add_device(DeviceListItem(name=name, port=port))

        if self.driver.device_manager.num_devices == 1:
            self.driver.device_manager.set_active_device(name)
            self.driver.gui.switch_proxy()

    def validate_new_device(self, name: str, port: str, device_list: list) -> bool:
        if not name or not port:
            self.view.display_error("Please input name and port for new device.")
            return False

        if len(device_list) >= self.MAX_DEVICES_LEN:
            self.view.display_error("You have reached the maximum number of devices.")
            return False

        for device in device_list:
            if device.ids.txt_device_name.text == name:
                self.view.display_error("Please input a unique device name.")
                return False
            if device.ids.txt_device_port.text == port:
                self.view.display_error("Please input a unique port.")
                return False

        return True

    def remove_device(self) -> None:
        """
        This function is called when the "Remove" button is clicked.
        """
        device_list = self.view.ids.box_device_list.children
        if len(device_list) == 0:
            self.view.display_error("No device is created.")
            return

        remove_devices = []
        for device in device_list:
            if device.ids.check_box_device.active:
                remove_devices.append(device)

        if len(remove_devices) == 0:
            self.view.display_error("No device is selected.")
            return
        assert self.driver.device_manager

        if len(remove_devices) == len(device_list):
            self.view.display_error(
                "At least one device must remain in the list.\nPlease ensure that you do not remove the last device."
            )
            return

        for device in remove_devices:
            self.view.ids.box_device_list.remove_widget(device)
            self.driver.device_manager.remove_device(device.name)

        if self.driver.device_manager.num_devices == 1:
            self.driver.device_manager.set_active_device(device_list[0].name)
            self.driver.gui.switch_proxy()
