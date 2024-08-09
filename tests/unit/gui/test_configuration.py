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
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import trio
from hypothesis import given
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.gui.controller.configuration_screen import (
    ConfigurationScreenController,
)
from local_console.gui.enums import ApplicationSchemaFilePath
from local_console.gui.enums import ApplicationType

from tests.fixtures.camera import cs_init
from tests.fixtures.gui import driver_set
from tests.strategies.configs import generate_text


@pytest.mark.trio
async def test_apply_configuration(driver_set, cs_init) -> None:
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
        driver, mock_gui = driver_set
        driver.camera_state = cs_init
        ctrl = ConfigurationScreenController(Mock(), driver)
        ctrl.apply_configuration()
        mock_apply_fb.assert_any_call()
        mock_apply_app_cfg.assert_any_call()


@pytest.mark.trio
async def test_apply_flatbuffers_schema(driver_set, cs_init, tmp_path) -> None:
    driver, mock_gui = driver_set
    async with trio.open_nursery() as nursery:
        driver.camera_state = cs_init
        model = driver.camera_state
        mock_gui.mdl.bind_vapp_file_functions(model)
        with (
            patch(
                "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
            ),
            patch(
                "local_console.gui.controller.configuration_screen.conform_flatbuffer_schema"
            ) as mock_conform_flatbuffers,
        ):
            ctrl = ConfigurationScreenController(Mock, driver)

            mock_gui.mdl.vapp_schema_file = ""
            ctrl.apply_flatbuffers_schema()
            ctrl.view.display_error.assert_called_with("Please select a schema file.")

            mock_gui.mdl.vapp_schema_file = tmp_path
            ctrl.apply_flatbuffers_schema()
            ctrl.view.display_error.assert_called_with(
                "Not a file or file does not exist!"
            )

            mock_conform_flatbuffers.side_effect = FlatbufferError(
                "Not a valid flatbuffers schema"
            )
            file = tmp_path / "file.bin"
            file.write_bytes(b"0")
            mock_gui.mdl.vapp_schema_file = str(file)
            ctrl.apply_flatbuffers_schema()
            ctrl.view.display_error.assert_called_with("Not a valid flatbuffers schema")

            mock_conform_flatbuffers.return_value = True
            mock_conform_flatbuffers.side_effect = None
            ctrl.apply_flatbuffers_schema()
            ctrl.view.display_info.assert_called_with("Success!")
            assert (
                mock_gui.mdl.vapp_schema_file
                == driver.camera_state.vapp_schema_file.value
            )
            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_apply_application_configuration(driver_set, cs_init, tmp_path) -> None:
    driver, mock_gui = driver_set
    async with trio.open_nursery() as nursery:
        driver.camera_state = cs_init
        model = driver.camera_state
        model.vapp_type.value = ApplicationType.CUSTOM.value
        mock_gui.mdl.bind_vapp_file_functions(model)
        with (
            patch(
                "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
            ),
            patch(
                "local_console.gui.controller.configuration_screen.map_class_id_to_name"
            ),
        ):
            ctrl = ConfigurationScreenController(Mock, driver)

            ctrl.apply_application_configuration()

            file = tmp_path / "config.json"
            mock_gui.mdl.vapp_config_file = file
            ctrl.apply_application_configuration()
            ctrl.view.display_error.assert_called_with(
                "App configuration does not exist"
            )

            file.write_text("{")
            ctrl.apply_application_configuration()
            ctrl.view.display_error.assert_called_with(
                "Error parsing app configuration JSON"
            )

            current_count_info = ctrl.view.display_info.call_count
            current_count_error = ctrl.view.display_error.call_count
            file.write_text('{"a": 3}')
            ctrl.apply_application_configuration()
            assert ctrl.view.display_info.call_count == current_count_info
            assert ctrl.view.display_error.call_count == current_count_error
            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_apply_application_configuration_error(
    driver_set, cs_init, tmp_path
) -> None:
    driver, mock_gui = driver_set
    async with trio.open_nursery() as nursery:
        driver.camera_state = cs_init
        model = driver.camera_state
        mock_gui.mdl.bind_vapp_file_functions(model)

        mock_view = MagicMock()
        with (
            patch(
                "local_console.gui.controller.configuration_screen.ConfigurationScreenView",
                return_value=mock_view,
            ),
            patch(
                "local_console.gui.controller.configuration_screen.json"
            ) as mock_json,
        ):
            ctrl = ConfigurationScreenController(Mock, driver)

            file = tmp_path / "labels.txt"
            file.write_text("class1\nclass2")
            driver.camera_state.vapp_labels_file.value = str(file)
            ctrl.apply_application_configuration()
            # Cast to Path if vapp_labels_file is str
            mock_view.display_error.assert_not_called()

            file = tmp_path / "config.json"
            file.write_text('{"a": 3}')

            mock_json.load.side_effect = Exception
            mock_gui.mdl.vapp_config_file = file
            ctrl.apply_application_configuration()
            ctrl.view.display_error.assert_called_with(
                "App configuration unknown error"
            )

            mock_json.load.side_effect = PermissionError
            ctrl.apply_application_configuration()
            ctrl.view.display_error.assert_called_with(
                "App configuration permission error"
            )
            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_update_application_type(driver_set, cs_init) -> None:
    driver, mock_gui = driver_set
    async with trio.open_nursery() as nursery:
        driver.camera_state = cs_init
        model = driver.camera_state
        model.vapp_type.value = ApplicationType.CUSTOM.value
        mock_gui.mdl.bind_vapp_file_functions(model)
        with (
            patch(
                "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
            ),
        ):
            ctrl = ConfigurationScreenController(Mock(), driver)

            mock_gui.mdl.vapp_type = ApplicationType.CUSTOM.value
            assert model.vapp_type.value == ApplicationType.CUSTOM
            assert ctrl.view.ids.labels_pick.disabled
            assert ctrl.view.ids.schema_pick.disabled

            mock_gui.mdl.vapp_type = ApplicationType.CLASSIFICATION
            assert model.vapp_type.value == ApplicationType.CLASSIFICATION
            assert model.vapp_schema_file.value == str(
                ApplicationSchemaFilePath.CLASSIFICATION
            )
            assert not ctrl.view.ids.labels_pick.disabled
            assert ctrl.view.ids.schema_pick.disabled

            mock_gui.mdl.vapp_type = ApplicationType.DETECTION
            assert model.vapp_type.value == ApplicationType.DETECTION
            assert model.vapp_schema_file.value == str(
                ApplicationSchemaFilePath.DETECTION
            )
            assert not ctrl.view.ids.labels_pick.disabled
            assert ctrl.view.ids.schema_pick.disabled

            mock_gui.mdl.vapp_type = ApplicationType.CUSTOM
            assert ctrl.view.ids.labels_pick.disabled
            assert not ctrl.view.ids.schema_pick.disabled
            nursery.cancel_scope.cancel()


@given(st.integers(min_value=1))
def test_update_total_max_size(value: int):
    driver = MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        ctrl = ConfigurationScreenController(MagicMock(), driver)
        ctrl.update_total_max_size(value)

        driver.camera_state.total_dir_watcher.set_storage_limit.assert_called_once_with(
            value
        )


@given(generate_text())
def test_update_image_directory(path: str):
    driver = MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        ctrl = ConfigurationScreenController(Mock(), driver)
        ctrl.update_image_directory(path)
        assert driver.camera_state.image_dir_path.value == Path(path)


@given(generate_text())
def test_update_inferences_directory(path: str):
    driver = MagicMock()
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        ctrl = ConfigurationScreenController(Mock(), driver)
        ctrl.update_inferences_directory(path)
        assert driver.camera_state.inference_dir_path.value == Path(path)


def test_get_view():
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        ctrl = ConfigurationScreenController(MagicMock(), MagicMock())
        assert ctrl.view == ctrl.get_view()


def test_refresh():
    with (
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenController.on_vapp_type"
        ) as mock_vapp_type,
        patch(
            "local_console.gui.controller.configuration_screen.ConfigurationScreenView"
        ),
    ):
        driver = MagicMock()
        ctrl = ConfigurationScreenController(MagicMock(), driver)
        ctrl.refresh()
        mock_vapp_type.assert_called_once_with(
            driver.device_manager.get_active_device_proxy(),
            driver.device_manager.get_active_device_state().vapp_type.value,
        )
