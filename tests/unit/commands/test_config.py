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
import json
from unittest.mock import AsyncMock
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from local_console.commands.config import app
from local_console.core.config import config_obj
from local_console.core.config import ConfigError
from local_console.core.enums import GetCommands
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import EVPParams
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from typer.testing import CliRunner

from tests.strategies.configs import generate_identifiers


runner = CliRunner()


def test_config_setget_command():
    result = runner.invoke(app, [GetCommands.GET.value])
    assert GlobalConfiguration(**json.loads(result.stdout)) == config_obj.get_config()


def test_config_setget_command_evp():
    result = runner.invoke(app, [GetCommands.GET.value, "evp"])
    assert EVPParams(**json.loads(result.stdout)) == config_obj.get_config().evp
    with patch.object(config_obj, "save_config"):
        runner.invoke(app, [GetCommands.SET.value, "evp.iot_platform", "tb"])
        result = runner.invoke(app, [GetCommands.GET.value, "evp"])
        assert "tb" == config_obj.get_config().evp.iot_platform


def test_config_get_command_active_device():
    result = runner.invoke(app, [GetCommands.GET.value, "active_device"])

    assert json.loads(result.stdout) == config_obj.get_config().active_device


def test_config_setget_command_devices():
    result = runner.invoke(app, [GetCommands.GET.value, "devices"])
    assert (
        DeviceConnection(**json.loads(result.stdout)[0])
        == config_obj.get_config().devices[0]
    )

    with patch.object(config_obj, "save_config"):
        runner.invoke(
            app,
            [GetCommands.SET.value, "--device", "Default", "mqtt.host", "192.168.1.1"],
        )
        result = runner.invoke(app, [GetCommands.GET.value, "devices"])
        assert (
            DeviceConnection(**json.loads(result.stdout)[0])
            == config_obj.get_config().devices[0]
        )
        assert config_obj.get_config().devices[0].mqtt.host == "192.168.1.1"
        runner.invoke(
            app,
            [GetCommands.SET.value, "--device", "Default", "mqtt.host", "localhost"],
        )


@given(
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
)
def test_config_instance_command(instance_id: str, method: str, params: str):
    with (
        patch("local_console.commands.config.Agent"),
        patch("local_console.commands.config.configure_task") as mock_configure,
    ):
        result = runner.invoke(app, ["instance", instance_id, method, params])
        mock_configure.assert_called_with(instance_id, method, params)
        assert result.exit_code == 0


@given(
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
)
def test_config_instance_command_exception(instance_id: str, method: str, params: str):
    with (
        patch("local_console.commands.config.Agent") as mock_agent,
        patch("local_console.commands.config.Agent.mqtt_scope") as mock_mqtt,
    ):
        mock_mqtt.side_effect = ConnectionError
        result = runner.invoke(app, ["instance", instance_id, method, params])
        mock_agent.assert_called()
        assert result.exit_code == 1


@given(st.integers(min_value=0, max_value=300), st.integers(min_value=0, max_value=300))
def test_config_device_command(interval_max: int, interval_min: int):
    with (
        patch("local_console.commands.config.Agent") as mock_agent,
        # patch("local_console.commands.config.Agent.determine_onwire_schema", return_value=),
        patch(
            "local_console.commands.config.config_device_task", return_value=0
        ) as mock_configure,
    ):
        mock_agent.determine_onwire_schema = AsyncMock(return_value=OnWireProtocol.EVP2)
        result = runner.invoke(app, ["device", f"{interval_max}", f"{interval_min}"])
        desired_device_config = DesiredDeviceConfig(
            reportStatusIntervalMax=interval_max, reportStatusIntervalMin=interval_min
        )
        mock_configure.assert_awaited_with(desired_device_config)
        assert result.exit_code == 0


@given(
    st.integers(min_value=-100, max_value=-1), st.integers(min_value=-100, max_value=-1)
)
def test_config_device_command_invalid_range(interval_max: int, interval_min: int):
    with (patch("local_console.commands.config.config_device_task") as mock_configure,):
        result = runner.invoke(app, ["device", interval_max, interval_min])
        mock_configure.assert_not_awaited()
        assert result.exit_code == 1


def test_config_unknown_device(caplog):

    with patch.object(config_obj, "get_device_config_by_name", side_effect=ConfigError):
        result = runner.invoke(
            app,
            [GetCommands.GET.value, "--device", "Unknown"],
        )
        assert result.exit_code == 1
        assert "Configuration error" in caplog.text
