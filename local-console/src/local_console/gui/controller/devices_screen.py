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

from local_console.gui.driver import Driver
from local_console.gui.model.devices_screen import DevicesScreenModel
from local_console.gui.view.common.components import DeviceItem
from local_console.gui.view.devices_screen.devices_screen import DevicesScreenView

logger = logging.getLogger(__name__)


class DevicesScreenController:
    """
    The `FirmwareScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: DevicesScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = DevicesScreenView(controller=self, model=self.model)

    def get_view(self) -> DevicesScreenView:
        return self.view

    def set_new_device_name(self, name: str) -> None:
        max_name_len = int(15)
        self.view.ids.txt_new_device_name.text = name[:max_name_len]

    def set_new_device_port(self, port: str) -> None:
        max_port_len = int(5)
        self.view.ids.txt_new_device_port.text = re.sub(r"\D", "", port)[:max_port_len]

    def add_new_device(self) -> None:
        max_devices_len = int(5)
        if len(self.view.ids.box_device_list.children) < max_devices_len:
            self.view.ids.box_device_list.add_widget(
                DeviceItem(
                    name=self.view.ids.txt_new_device_name.text,
                    port=self.view.ids.txt_new_device_port.text,
                )
            )

    def remove_device(self) -> None:
        device_list = self.view.ids.box_device_list.children
        remove_devices = []
        for device in device_list:
            if isinstance(device, DeviceItem) and device.ids.check_box_device.active:
                remove_devices.append(device)
        for device in remove_devices:
            self.view.ids.box_device_list.remove_widget(device)
