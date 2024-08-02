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
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio

patch("local_console.gui.view.common.components.DeviceItem").start()

from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.device_manager import DeviceManager
from local_console.gui.controller.devices_screen import DevicesScreenController
from local_console.gui.model.devices_screen import DevicesScreenModel
from local_console.core.camera.state import CameraState
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.clients.agent import Agent

from pytest import mark


def test_get_view():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)
        assert ctrl.view == ctrl.get_view()


def test_restore_device_list_single_item():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)
        ctrl.add_device_to_device_list = MagicMock()

        device_config = [DeviceListItem(name="test_device_1", port="1234")]
        ctrl.restore_device_list(device_config)
        ctrl.add_device_to_device_list.assert_called_once()


def test_restore_device_list_multiple_items():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)
        ctrl.add_device_to_device_list = MagicMock()

        device_config = [
            DeviceListItem(name="test_device_1", port="1234"),
            DeviceListItem(name="test_device_2", port="5678"),
        ]
        ctrl.restore_device_list(device_config)
        assert ctrl.add_device_to_device_list.call_count == 2


@mark.parametrize(
    "port, expected",
    [("", ""), ("0", "0"), ("65535", "65535"), ("65536", "6553"), ("655351", "65535")],
)
def test_set_new_device_port(port, expected):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)
        ctrl.set_device_port_text = MagicMock()

        ctrl.set_new_device_port(port)
        ctrl.set_device_port_text.assert_called_once_with(expected)


@mark.parametrize(
    "name, port, error_message",
    [
        ("", "", "Please input name and port for new device."),
        ("test_device_1", "", "Please input name and port for new device."),
        ("", "1234", "Please input name and port for new device."),
    ],
)
def test_add_new_device_invalid_name_port(name, port, error_message):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        ctrl.view.ids.txt_new_device_name.text = name
        ctrl.view.ids.txt_new_device_port.text = port
        ctrl.add_device_to_device_list = MagicMock()
        ctrl.add_new_device()

        ctrl.view.display_error.assert_called_once_with(error_message)
        ctrl.add_device_to_device_list.assert_not_called()


@mark.parametrize(
    "name, port, error_message",
    [
        ("test_device_1", "1234", "You have reached the maximum number of devices."),
    ],
)
def test_add_new_device_invalid_device_list(name, port, error_message):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device_list = [f"device_{i}" for i in range(1, 17)]

        ctrl.view.ids.txt_new_device_name.text = name
        ctrl.view.ids.txt_new_device_port.text = port
        ctrl.view.ids.box_device_list.children = device_list
        ctrl.add_device_to_device_list = MagicMock()
        ctrl.add_new_device()

        ctrl.view.display_error.assert_called_once_with(error_message)
        ctrl.add_device_to_device_list.assert_not_called()


@mark.parametrize(
    "name, port, error_message",
    [
        ("test_device_1", "1234", "Please input a unique device name."),
    ],
)
def test_add_new_device_invalid_unique_name(name, port, error_message):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device = MagicMock()
        device.ids.txt_device_name.text = name
        device.ids.txt_device_port.text = port
        device_list = [device]

        ctrl.view.ids.txt_new_device_name.text = name
        ctrl.view.ids.txt_new_device_port.text = port
        ctrl.view.ids.box_device_list.children = device_list
        ctrl.add_device_to_device_list = MagicMock()
        ctrl.add_new_device()

        ctrl.view.display_error.assert_called_once_with(error_message)
        ctrl.add_device_to_device_list.assert_not_called()


@mark.parametrize(
    "name, port, error_message",
    [
        ("test_device_1", "1234", "Please input a unique port."),
    ],
)
def test_add_new_device_invalid_unique_port(name, port, error_message):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device = MagicMock()
        device.ids.txt_device_name.text = "test_device_0"
        device.ids.txt_device_port.text = port
        device_list = [device]

        ctrl.view.ids.txt_new_device_name.text = name
        ctrl.view.ids.txt_new_device_port.text = port
        ctrl.view.ids.box_device_list.children = device_list
        ctrl.add_device_to_device_list = MagicMock()
        ctrl.add_new_device()

        ctrl.view.display_error.assert_called_once_with(error_message)
        ctrl.add_device_to_device_list.assert_not_called()


def generate_params_for_error_message() -> list:
    device1 = MagicMock()
    device1.ids.check_box_device.active = False
    device_list_1 = [device1]
    return [
        ("", "No device is created."),
        (device_list_1, "No device is selected."),
    ]


@mark.parametrize("device_list, error_message", generate_params_for_error_message())
def test_remove_device_no_device_selected(device_list, error_message):
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        ctrl.view.ids.box_device_list.children = device_list
        ctrl.driver.device_manager.remove_device = MagicMock()

        ctrl.remove_device()
        ctrl.view.display_error.assert_called_once_with(error_message)
        ctrl.driver.device_manager.remove_device.assert_not_called()


def test_remove_device():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device1 = MagicMock()
        device1.ids.check_box_device.active = True
        device1.name = "test_device_01"
        device_list = [device1]
        ctrl.view.ids.box_device_list.children = device_list

        ctrl.driver.device_manager.remove_device = MagicMock()
        ctrl.remove_device()
        ctrl.driver.device_manager.remove_device.assert_called_once_with(device1.name)


def test_devices_screen():
    model, mock_driver = DevicesScreenModel(), MagicMock()
    with patch("local_console.gui.controller.devices_screen.DevicesScreenView"):
        ctrl = DevicesScreenController(model, mock_driver)

        device_name = "test-device"
        ctrl.set_new_device_name(device_name)
        assert ctrl.view.ids.txt_new_device_name.text == device_name

        device_port = "1234"
        ctrl.set_new_device_port(device_port)
        assert ctrl.view.ids.txt_new_device_port.text == device_port

        device_name = "test-device-12345"
        ctrl.set_new_device_name(device_name)
        assert ctrl.view.ids.txt_new_device_name.text == device_name[:15]

        device_port = "1234567"
        ctrl.set_new_device_port(device_port)
        assert ctrl.view.ids.txt_new_device_port.text == device_port[:5]

        ctrl.add_new_device()
        ctrl.remove_device()


@pytest.mark.trio
async def test_device_manager(nursery):
    with (
        patch("local_console.gui.device_manager.add_device_to_config") as mock_add_dev,
        patch("local_console.gui.device_manager.get_device_configs") as mock_get_dev,
        patch("local_console.gui.device_manager.remove_device_config") as mock_remove,
        patch(
            "local_console.gui.device_manager.DeviceManager.bind_state_proxy"
        ) as mock_add_internals,
    ):
        send_channel, _ = trio.open_memory_channel(0)
        device_manager = DeviceManager(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )

        device = DeviceListItem(name="test_device", port="1234")

        device_manager.add_device(device)
        mock_add_dev.assert_called_once()
        mock_add_internals.assert_called_once()
        assert len(device_manager.proxies_factory) == device_manager.num_devices
        assert len(device_manager.state_factory) == device_manager.num_devices
        assert len(device_manager.agent_factory) == device_manager.num_devices

        device_manager.remove_device(device.name)
        mock_remove.assert_called_once()

        assert len(device_manager.proxies_factory) == device_manager.num_devices
        assert len(device_manager.state_factory) == device_manager.num_devices
        assert len(device_manager.agent_factory) == device_manager.num_devices

        device_manager.get_device_config()
        assert mock_get_dev.call_count == 3


@pytest.mark.trio
async def test_device_manager_with_config(nursery):
    with (patch("local_console.core.config.config_paths") as mock_config_paths,):
        app_subdir = Path("local-console")
        dummy_home = Path("/tmp/test_devices")
        dummy_default_home = dummy_home / ".config" / app_subdir
        dummy_config_path = dummy_default_home / "config.ini"

        mock_config_paths.config_path = dummy_config_path
        from local_console.core.config import setup_default_config

        setup_default_config()
        send_channel, _ = trio.open_memory_channel(0)
        device_manager = DeviceManager(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )
        assert device_manager.get_device_config() == []

        device1 = DeviceListItem(name="test_device_1", port="1234")
        device2 = DeviceListItem(name="test_device_2", port="23456")
        device3 = DeviceListItem(name="test_device_3", port="7890")

        device_manager.add_device(device1)
        device_items = device_manager.get_device_config()
        assert device_items[0] == device1
        device_manager.set_active_device(device1.name)

        state_1 = device_manager.get_active_device_state()
        assert isinstance(state_1, CameraState)
        proxy_1 = device_manager.get_active_device_proxy()
        assert isinstance(proxy_1, CameraStateProxy)
        mqtt_1 = device_manager.get_active_mqtt_client()
        assert isinstance(mqtt_1, Agent)

        device_manager.add_device(device2)
        device_manager.add_device(device3)
        device_items = device_manager.get_device_config()
        assert device_items[0] == device1
        assert device_items[1] == device2
        assert device_items[2] == device3

        device_manager.set_active_device(device2.name)

        state_2 = device_manager.get_active_device_state()
        assert state_2 != state_1
        proxy_2 = device_manager.get_active_device_proxy()
        assert proxy_2 != proxy_1
        mqtt_2 = device_manager.get_active_mqtt_client()
        assert mqtt_2 != mqtt_1

        device_manager.remove_device(device2.name)
        device_items = device_manager.get_device_config()
        assert device_items[0] == device1
        assert device_items[1] == device3

        device_manager.remove_device(device1.name)
        device_manager.remove_device(device3.name)
        device_items = device_manager.get_device_config()
        assert device_items == []

        if dummy_home.is_dir:
            shutil.rmtree(dummy_home)
