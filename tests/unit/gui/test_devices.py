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
from unittest.mock import MagicMock
from unittest.mock import patch

patch("local_console.gui.view.common.components.DeviceItem").start()

from local_console.gui.controller.devices_screen import DevicesScreenController
from local_console.gui.model.devices_screen import DevicesScreenModel


def test_get_view():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)
        assert ctrl.view == ctrl.get_view()


def test_devices_screen():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device_name = "test device"
        ctrl.set_new_device_name(device_name)
        assert ctrl.view.ids.txt_new_device_name.text == device_name

        device_name = "test device 12345"
        ctrl.set_new_device_name(device_name)
        assert ctrl.view.ids.txt_new_device_name.text == device_name[:15]

        device_port = "1234"
        ctrl.set_new_device_port(device_port)
        assert ctrl.view.ids.txt_new_device_port.text == device_port

        device_port = "1234567"
        ctrl.set_new_device_port(device_port)
        assert ctrl.view.ids.txt_new_device_port.text == device_port[:5]

        ctrl.add_new_device()
        ctrl.remove_device()
