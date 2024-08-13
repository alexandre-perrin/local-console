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
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
import trio
from local_console.commands.broker import app
from local_console.core.config import config_obj
from local_console.servers.broker import BrokerException
from local_console.servers.broker import spawn_broker
from typer.testing import CliRunner

runner = CliRunner()


def test_broker_command():
    with (
        patch("local_console.commands.broker.spawn_broker") as mock_spawn,
        patch("local_console.commands.broker.sleep_forever"),
    ):
        result = runner.invoke(app, [])
        mock_spawn.assert_called_once_with(
            config_obj.get_active_device_config().mqtt.port, ANY, False
        )
        assert result.exit_code == 0


def test_broker_command_error():
    with (
        patch(
            "local_console.commands.broker.spawn_broker", side_effect=BrokerException
        ) as mock_spawn,
        patch("trio.sleep_forever"),
    ):
        result = runner.invoke(app, [])
        mock_spawn.assert_called_once_with(
            config_obj.get_active_device_config().mqtt.port, ANY, False
        )
        assert result.exit_code == 1


@pytest.mark.trio
async def test_spawn_broker_command_port_already_in_use(nursery):

    error_text = b"Error: Address already in use"
    mock_process = AsyncMock()
    mock_process.stdout.receive_some.return_value = error_text

    async def mock_broker_process(*args, task_status=trio.TASK_STATUS_IGNORED):
        task_status.started(mock_process)

    with (
        patch("local_console.servers.broker.which"),
        patch("local_console.servers.broker.partial", return_value=mock_broker_process),
        # This is the test assertion:
        pytest.raises(BrokerException),
    ):
        async with spawn_broker(1111, nursery, False):
            pass

    assert len(nursery.child_tasks) == 0
