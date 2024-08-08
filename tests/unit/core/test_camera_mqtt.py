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
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.gui.device_manager import DeviceManager

from tests.fixtures.camera import cs_init
from tests.fixtures.driver import mock_driver_with_agent


@pytest.mark.trio
async def test_process_incoming_telemetry(cs_init) -> None:
    with patch("local_console.core.camera.mixin_mqtt.datetime") as mock_time:
        camera = cs_init

        mock_now = Mock()
        mock_time.now.return_value = mock_now

        dummy_telemetry = {"a": "b"}
        await camera.process_incoming("v1/devices/me/telemetry", dummy_telemetry)

        assert camera._last_reception == mock_now


@pytest.mark.trio
async def test_streaming_rpc_stop(cs_init):
    with (mock_driver_with_agent() as (driver, mock_agent),):

        mock_agent.publish = AsyncMock()
        mock_rpc = AsyncMock()
        mock_agent.rpc = mock_rpc

        driver.camera_state = cs_init
        driver.device_manager = DeviceManager(Mock(), Mock(), Mock())
        driver.device_manager.init_devices([])
        driver.device_manager.get_active_device_state().mqtt_client = mock_agent

        await driver.streaming_rpc_stop()
        mock_rpc.assert_awaited_with(
            "backdoor-EA_Main", "StopUploadInferenceData", "{}"
        )
