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

from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.devices_screen import DevicesScreenModel
from local_console.gui.utils.sync_async import run_on_ui_thread
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

        self.restore_device_list(config_obj.get_device_list_items())

    def get_view(self) -> DevicesScreenView:
        return self.view

    def restore_device_list(self, device_config_items: list[DeviceListItem]) -> None:
        """
        This function is called on init to restore device list from configuration.
        """
        for item in device_config_items:
            self.add_device_to_device_list(item)
        self.driver.gui.switch_proxy()

    @run_on_ui_thread
    def add_device_to_device_list(self, item: DeviceListItem) -> None:
        widget = DeviceItem(name=item.name, port=item.port)
        widget.bind(on_name_edited=self.on_rename_typed)
        widget.bind(on_name_enter=self.on_rename_hit_enter)
        self.view.ids.box_device_list.add_widget(widget)

        assert self.driver.device_manager
        if self.driver.device_manager.num_devices == 1:
            self.driver.device_manager.set_active_device(item.port)

    def on_rename_typed(self, device_widget: DeviceItem, name: str) -> None:
        device_widget.schedule_delayed_update(
            lambda dt: self.rename_device(device_widget, name)
        )

    def on_rename_hit_enter(self, device_widget: DeviceItem, name: str) -> None:
        device_widget.cancel_delayed_update()
        self.rename_device(device_widget, name)

    def rename_device(self, device_widget: DeviceItem, name: str) -> None:
        assert self.driver
        assert self.driver.device_manager

        port = device_widget.port
        self.driver.device_manager.rename_device(port, name)
        self.driver.gui.refresh_active_device()
        self.view.display_info("Device renamed", f"'{name}' connecting on port {port}")

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

    def register_new_device(self) -> None:
        """
        This function is called when user inputs name.
        """
        name = self.view.ids.txt_new_device_name.text
        port = int(self.view.ids.txt_new_device_port.text)
        device_list = self.view.ids.box_device_list.children

        if not self.validate_new_device(name, port, device_list):
            return

        assert self.driver.device_manager

        # Save device list into device configuration
        item = DeviceListItem(name=name, port=port)
        self.driver.from_sync(
            self.driver.device_manager.add_device,
            item,
            self.add_device_to_device_list,
        )

    def validate_new_device(self, name: str, port: int, device_list: list) -> bool:
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
            if device.ids.txt_device_port.text == str(port):
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
            self.driver.device_manager.remove_device(device.port)

        if self.driver.device_manager.num_devices == 1:
            self.driver.device_manager.set_active_device(device_list[0].port)
            self.driver.gui.switch_proxy()

        self.driver.gui.refresh_active_device()
