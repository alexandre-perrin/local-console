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
from unittest.mock import patch

from local_console.commands.broker import app
from typer.testing import CliRunner

runner = CliRunner()


def test_broker_command():
    with (
        patch("local_console.commands.broker.get_config") as mock_config,
        patch("local_console.commands.broker.spawn_broker") as mock_spawn,
        patch("trio.sleep_forever"),
    ):
        result = runner.invoke(app, [])
        mock_spawn.assert_called_once_with(mock_config.return_value.mqtt.port, ANY, ANY)
        assert result.exit_code == 0
