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
from local_console.gui.model.configuration_screen import ConfigurationScreenModel


def test_apply_configuration():
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
        patch.object(
            ConfigurationScreenController, "apply_flatbuffers_schema"
        ) as mock_apply_fb,
        patch.object(
            ConfigurationScreenController, "apply_application_configuration"
        ) as mock_apply_app_cfg,
    ):
        ctrl = ConfigurationScreenController(ConfigurationScreenModel(), MagicMock())
        ctrl.apply_configuration()
        mock_apply_fb.assert_any_call()
        mock_apply_app_cfg.assert_any_call()


def test_apply_flatbuffers_schema(tmpdir):
    model, mock_driver = ConfigurationScreenModel(), MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
        patch(
            "local_console.gui.controller.configuration_screen.FlatBuffers"
        ) as mock_flatbuffers,
    ):
        ctrl = ConfigurationScreenController(model, mock_driver)
        model.flatbuffers_schema = None
        ctrl.apply_flatbuffers_schema()
        assert model.flatbuffers_process_result == "Please select a schema file."

        model.flatbuffers_schema = Path(tmpdir)
        ctrl.apply_flatbuffers_schema()
        assert model.flatbuffers_process_result == "Not a file or file does not exist!"

        mock_flatbuffers.return_value.conform_flatbuffer_schema.return_value = (
            False,
            None,
        )
        file = Path(tmpdir) / "file.bin"
        file.write_bytes(b"0")
        model.flatbuffers_schema = file
        ctrl.apply_flatbuffers_schema()
        assert model.flatbuffers_process_result == "Not a valid flatbuffers schema"

        assert mock_driver.flatbuffers_schema != model.flatbuffers_schema
        mock_flatbuffers.return_value.conform_flatbuffer_schema.return_value = (
            True,
            None,
        )
        ctrl.apply_flatbuffers_schema()
        assert model.flatbuffers_process_result == "Success!"
        assert mock_driver.flatbuffers_schema == model.flatbuffers_schema


def test_apply_application_configuration(tmpdir):
    model, mock_driver = ConfigurationScreenModel(), MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        ctrl = ConfigurationScreenController(model, mock_driver)

        ctrl.apply_application_configuration()
        assert model.flatbuffers_process_result is None

        file = Path(tmpdir) / "config.json"
        ctrl.update_app_configuration(str(file))
        ctrl.apply_application_configuration()
        assert model.flatbuffers_process_result == "App configuration does not exist"

        file.write_text("{")
        ctrl.apply_application_configuration()
        assert model.flatbuffers_process_result == "Error parsin app configuration JSON"

        file.write_text('{"a": 3}')
        model.flatbuffers_process_result = ""
        ctrl.apply_application_configuration()
        assert model.flatbuffers_process_result == ""
