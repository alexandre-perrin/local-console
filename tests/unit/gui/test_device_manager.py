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
from contextlib import asynccontextmanager
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import trio
from hypothesis import given
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceListItem
from local_console.gui.device_manager import DeviceHandlingError
from local_console.gui.device_manager import DeviceManager

from tests.strategies.configs import generate_identifiers


@asynccontextmanager
async def mock_persistency_update(result=True):
    async def mock_mqtt_setup(*args, task_status=trio.TASK_STATUS_IGNORED):
        task_status.started(result)

    async with trio.open_nursery() as nursery:
        device_manager = DeviceManager(Mock(), nursery, Mock())

        with (
            patch.object(
                device_manager, "_update_from_persistency"
            ) as mock_persistency,
            patch("local_console.gui.device_manager.config_obj.save_config"),
            patch(
                "local_console.gui.device_manager.CameraState.startup",
                new=mock_mqtt_setup,
            ),
        ):
            await device_manager.init_devices([])
            yield mock_persistency, device_manager


@given(
    generate_identifiers(max_size=5),
)
@pytest.mark.trio
async def test_update_module_file_persists(module_file: str):
    async with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        state.module_file.value = module_file

        mock_persistency.assert_called_with(device_manager.active_device.port)


@given(
    generate_identifiers(max_size=5),
)
@pytest.mark.trio
async def test_update_ai_model_file_persists(ai_model_file: str):
    async with mock_persistency_update() as (mock_persistency, device_manager):
        state = device_manager.get_active_device_state()
        config = config_obj.get_active_device_config().persist
        config.ai_model_file = "not a file"
        state.ai_model_file.value = ai_model_file
        assert config.ai_model_file == ai_model_file
        mock_persistency.assert_called_with(device_manager.active_device.port)


@pytest.mark.trio
async def test_init_devices_with_empty_list():
    async with mock_persistency_update() as (mock_persistency, device_manager):
        default_device = DeviceListItem(
            name=DeviceManager.DEFAULT_DEVICE_NAME,
            port=str(DeviceManager.DEFAULT_DEVICE_PORT),
        )
        assert device_manager.active_device == default_device


@pytest.mark.trio
async def test_device_manager(nursery):
    send_channel, _ = trio.open_memory_channel(0)
    device_manager = DeviceManager(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    with (patch.object(device_manager, "initialize_persistency"),):
        assert len(device_manager.proxies_factory) == 0
        assert len(device_manager.state_factory) == 0

        device = DeviceListItem(name="test_device", port="1234")
        await device_manager.add_device(device)
        assert len(device_manager.proxies_factory) == 1
        assert len(device_manager.state_factory) == 1
        assert (
            device_manager.proxies_factory[1234].mqtt_host
            == device_manager.state_factory[1234].mqtt_host.value
        )
        assert (
            int(device_manager.proxies_factory[1234].mqtt_port)
            == device_manager.state_factory[1234].mqtt_port.value
        )
        assert (
            device_manager.proxies_factory[1234].ntp_host
            == device_manager.state_factory[1234].ntp_host.value
        )

        with pytest.raises(DeviceHandlingError):
            device_manager.remove_device(device.name)


@pytest.mark.trio
async def test_device_manager_with_config():
    async with mock_persistency_update() as (mock_persistency, device_manager):

        assert len(device_manager.proxies_factory) == 1
        assert len(device_manager.state_factory) == 1

        device = DeviceListItem(name="test_device", port=1234)
        continuation_fn = Mock()
        await device_manager.add_device(device, continuation_fn)
        continuation_fn.assert_called_once_with(device)
        assert len(device_manager.proxies_factory) == 2
        assert len(device_manager.state_factory) == 2

        device_manager.set_active_device(1234)
        device_manager.rename_device(1234, "renamed_device")
        assert config_obj.get_active_device_config().name == "renamed_device"

        device_manager.remove_device(device.port)
        assert len(device_manager.proxies_factory) == 1
        assert len(device_manager.state_factory) == 1


@pytest.mark.trio
async def test_device_manager_add_invalid_port_same_name_retry_failure(nursery):

    async with mock_persistency_update(result=False) as (
        mock_persistency,
        device_manager,
    ):
        with (patch.object(device_manager, "initialize_persistency"),):
            send_channel, _ = trio.open_memory_channel(0)
            device_manager = DeviceManager(
                send_channel, nursery, trio.lowlevel.current_trio_token()
            )
            assert len(device_manager.proxies_factory) == 0
            assert len(device_manager.state_factory) == 0

            device = DeviceListItem(name="test_device", port="1234")
            await device_manager.add_device(device)
            assert len(device_manager.proxies_factory) == 0
            assert len(device_manager.state_factory) == 0

    async with mock_persistency_update() as (mock_persistency, device_manager):
        send_channel, _ = trio.open_memory_channel(0)
        device_manager = DeviceManager(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )
        with (patch.object(device_manager, "initialize_persistency"),):
            device = DeviceListItem(name="test_device", port="4567")
            await device_manager.add_device(device)
            assert len(device_manager.proxies_factory) == 1
            assert len(device_manager.state_factory) == 1
            # The actual plus default one
            assert len(config_obj.get_config().devices) == 2
            assert config_obj.get_config().devices[1].name == "test_device"
            assert config_obj.get_config().devices[1].mqtt.port == 4567
