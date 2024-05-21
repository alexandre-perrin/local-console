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
from unittest.mock import MagicMock
from unittest.mock import patch

from local_console.gui.controller.configuration_screen import (
    ConfigurationScreenController,
)


def test_a(tmpdir):
    mock_model, mock_driver = MagicMock(), MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
        patch(
            "local_console.gui.controller.configuration_screen.FlatBuffers"
        ) as mock_flatbuffers,
    ):
        ctrl = ConfigurationScreenController(mock_model, mock_driver)
        mock_model.flatbuffers_schema = None
        ctrl.process_schema()
        assert mock_model.flatbuffers_process_result == "Please select a schema file."

        mock_model.flatbuffers_schema = Path(tmpdir)
        ctrl.process_schema()
        assert (
            mock_model.flatbuffers_process_result
            == "Not a file or file does not exist!"
        )

        mock_flatbuffers.return_value.conform_flatbuffer_schema.return_value = (
            False,
            None,
        )
        file = Path(tmpdir) / "file.bin"
        file.write_bytes(b"0")
        mock_model.flatbuffers_schema = file
        ctrl.process_schema()
        assert mock_model.flatbuffers_process_result == "Not a valid flatbuffers schema"

        assert mock_driver.flatbuffers_schema != mock_model.flatbuffers_schema
        mock_flatbuffers.return_value.conform_flatbuffer_schema.return_value = (
            True,
            None,
        )
        ctrl.process_schema()
        assert mock_model.flatbuffers_process_result == "Success!"
        assert mock_driver.flatbuffers_schema == mock_model.flatbuffers_schema
