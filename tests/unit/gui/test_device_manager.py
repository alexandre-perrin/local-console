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
from local_console.core.config import config_to_schema
from local_console.core.config import get_default_config
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.device_manager import DeviceManager

from tests.strategies.configs import generate_identifiers


@contextmanager
def mock_persistency_update():
    device = DeviceListItem(name="device_name", port="1234")
    with (
        patch(
            "local_console.gui.device_manager.add_device_to_config",
        ),
        patch(
            "local_console.gui.device_manager.get_config",
            return_value=config_to_schema(get_default_config()),
        ),
        patch(
            "local_console.core.camera.state.update_device_persistent_config"
        ) as mock_persistency,
        patch(
            "local_console.core.camera.state.get_device_persistent_config",
            return_value={},
        ),
        patch(
            "local_console.gui.device_manager.get_device_configs",
            return_value=[device],
        ),
    ):
        device_manager = DeviceManager(Mock(), Mock(), Mock())
        device_manager.init_devices([device])
        device_manager.set_active_device(device.name)
        yield mock_persistency, device_manager


@given(
    generate_identifiers(max_size=5),
)
def test_update_module_file_persists(module_file: str):
    with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        state.module_file.value = module_file

        config = state._create_persister()
        config.module_file = module_file
        mock_persistency.assert_called_with(
            device_manager.active_device.name, config.model_dump()
        )


@given(
    generate_identifiers(max_size=5),
)
@settings(deadline=1000)
def test_update_ai_model_file_persists(ai_model_file: str):
    with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        state.ai_model_file.value = ai_model_file

        config = state._create_persister()
        config.ai_model_file = ai_model_file
        mock_persistency.assert_called_with(
            device_manager.active_device.name, config.model_dump()
        )
