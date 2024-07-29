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
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.camera.ai_model import deploy_step
from local_console.core.camera.ai_model import undeploy_step
from local_console.core.camera.state import CameraState
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.config import config_to_schema
from local_console.core.config import get_default_config
from local_console.utils.local_network import get_my_ip_by_routing


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


@pytest.fixture(params=["000001"])
def network_id(request):
    return request.param


def mock_get_config():
    return config_to_schema(get_default_config())


@pytest.fixture(autouse=True)
def fixture_get_config():
    with patch(
        "local_console.core.camera.ai_model.get_config",
        mock_get_config,
    ) as _fixture:
        yield _fixture


@pytest.mark.trio
async def test_undeploy_step_rpc_sent(network_id: str):
    camera_state = CameraState()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with (
        patch("local_console.core.camera.ai_model.Agent", return_value=mock_agent),
        patch.object(camera_state, "device_config") as mock_config,
    ):
        mock_config.value.OTA.UpdateStatus = "Done"
        await undeploy_step(camera_state, network_id, MagicMock())
        payload = (
            f'{{"OTA":{{"UpdateModule":"DnnModel","DeleteNetworkID":"{network_id}"}}}}'
        )
        mock_agent.configure.assert_called_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )


@pytest.mark.trio
async def test_undeploy_step_not_deployed_model(update_status: str):
    camera_state = CameraState()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with (
        patch("local_console.core.camera.ai_model.Agent", return_value=mock_agent),
        patch.object(camera_state, "device_config") as mock_config,
        patch.object(camera_state, "ota_event") as mock_ota_event,
    ):
        mock_config.value.OTA.UpdateStatus = update_status
        await undeploy_step(camera_state, "000001", MagicMock())
        mock_ota_event.assert_not_awaited()


@pytest.mark.trio
async def test_deploy_step(tmp_path, network_id, update_status: str):
    filename = "dummy.bin"
    tmp_file = tmp_path / filename

    camera_state = CameraState()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()

    with (
        patch("local_console.core.camera.ai_model.Agent", return_value=mock_agent),
        patch.object(camera_state, "device_config") as mock_config,
        patch.object(camera_state, "ota_event") as mock_ota_event,
        patch(
            "local_console.core.camera.ai_model.AsyncWebserver",
            return_value=mock_agent,
        ),
        patch(
            "local_console.core.camera.ai_model.get_network_ids",
            return_value=[network_id],
        ),
    ):
        mock_config.value.OTA.UpdateStatus = update_status
        with open(tmp_file, "w") as f:
            f.write("dummy")
        await deploy_step(camera_state, network_id, tmp_file, MagicMock())
        hashvalue = get_package_hash(tmp_file)
        payload = (
            '{"OTA":{"UpdateModule":"DnnModel","DesiredVersion":"",'
            f'"PackageUri":"http://{get_my_ip_by_routing()}:8000/dummy.bin",'
            f'"HashValue":"{hashvalue}"'
            "}}"
        )
        mock_agent.configure.assert_called_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )
        mock_ota_event.assert_not_awaited()
