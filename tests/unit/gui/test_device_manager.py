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
from contextlib import contextmanager
from unittest.mock import Mock
from unittest.mock import patch

from hypothesis import given
from hypothesis import settings
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.device_manager import DeviceManager

from tests.strategies.configs import generate_identifiers


@contextmanager
def mock_persistency_update():
    device_manager = DeviceManager(Mock(), Mock(), Mock())
    with (
        patch.object(device_manager, "_update_from_persistency") as mock_persistency,
    ):
        device_manager.set_active_device(
            config_obj.get_active_device_config().mqtt.port
        )
        device_manager.init_devices(config_obj.get_device_configs())
        yield mock_persistency, device_manager


@given(
    generate_identifiers(max_size=5),
)
def test_update_module_file_persists(module_file: str):
    with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        state.module_file.value = module_file

        mock_persistency.assert_called_with(device_manager.active_device.port)


@given(
    generate_identifiers(max_size=5),
)
@settings(deadline=1000)
def test_update_ai_model_file_persists(ai_model_file: str):
    with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        config = config_obj.get_active_device_config().persist
        config.ai_model_file = "not a file"
        state.ai_model_file.value = ai_model_file
        assert config.ai_model_file == ai_model_file
        mock_persistency.assert_called_with(device_manager.active_device.port)


def test_init_devices_with_empty_list():
    device_manager = DeviceManager(Mock(), Mock(), Mock())
    with patch.object(device_manager, "add_device"):
        device_manager.init_devices([])

        default_device = DeviceListItem(
            name=DeviceManager.DEFAULT_DEVICE_NAME,
            port=str(DeviceManager.DEFAULT_DEVICE_PORT),
        )

        device_manager.active_device == default_device
        device_manager.add_device.assert_called_once_with(default_device)
