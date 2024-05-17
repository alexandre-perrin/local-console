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
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from local_console.commands.new import app
from typer.testing import CliRunner

from tests.strategies.configs import generate_text

runner = CliRunner()


@given(
    generate_text(),
    st.lists(generate_text(), min_size=1),
)
def test_new_command(name: str, path_mock: str):
    assets_mock = Mock()
    assets_mock.__path__ = path_mock

    with (
        patch("local_console.commands.new.assets", assets_mock),
        patch("local_console.commands.new.shutil.copytree") as mock_copytree,
        patch("local_console.commands.new.shutil.move") as mock_move,
    ):
        project_path = Path(name)
        result = runner.invoke(app, ["-p", name])
        mock_copytree.assert_called_once_with(
            path_mock[0], project_path, dirs_exist_ok=True
        )
        mock_move.assert_called_once_with(
            project_path / "template", project_path / project_path
        )
        assert result.exit_code == 0
