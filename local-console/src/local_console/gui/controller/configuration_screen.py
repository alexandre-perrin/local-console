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
import logging
from pathlib import Path

from local_console.core.camera.flatbuffers import conform_flatbuffer_schema
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import map_class_id_to_name
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.enums import ApplicationSchemaFilePath
from local_console.gui.enums import ApplicationType
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.model.configuration_screen import ConfigurationScreenModel
from local_console.gui.view.configuration_screen.configuration_screen import (
    ConfigurationScreenView,
)


logger = logging.getLogger(__file__)


class ConfigurationScreenController(BaseController):
    """
    The `ConfigurationScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ConfigurationScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = ConfigurationScreenView(controller=self, model=self.model)

        self.bind()

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(vapp_type=self.on_vapp_type)
        self.view.ids.lbl_file_selector.ids.lbl_number.unbind(text=self.on_size)
        self.view.ids.lbl_file_selector.ids.lbl_unit.unbind(text=self.on_unit)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(vapp_type=self.on_vapp_type)
        self.view.ids.lbl_file_selector.ids.lbl_number.bind(text=self.on_size)
        self.view.ids.lbl_file_selector.ids.lbl_unit.bind(text=self.on_unit)

    def refresh(self) -> None:
        assert self.driver.device_manager
        proxy = self.driver.device_manager.get_active_device_proxy()
        state = self.driver.device_manager.get_active_device_state()
        assert state.vapp_type.value
        self.on_vapp_type(
            proxy,
            state.vapp_type.value,
        )

    def on_size(self, instance: CameraStateProxy, value: str) -> None:
        self.driver.gui.mdl.size = value

    def on_unit(self, instance: CameraStateProxy, value: str) -> None:
        self.driver.gui.mdl.unit = value

    def on_vapp_type(
        self, instance: CameraStateProxy, app_type: ApplicationType
    ) -> None:
        is_custom = app_type == ApplicationType.CUSTOM.value
        self.view.ids.labels_pick.disabled = is_custom
        self.view.ids.schema_pick.disabled = not is_custom
        assert self.driver.camera_state

        if app_type == ApplicationType.CUSTOM.value:
            self.driver.gui.mdl.vapp_schema_file = ""
            self.view.ids.schema_pick.select_path("")

        elif app_type == ApplicationType.CLASSIFICATION.value:
            path = ApplicationSchemaFilePath.CLASSIFICATION
            self.driver.gui.mdl.vapp_schema_file = str(path)
            self.view.ids.schema_pick.select_path(str(path))

        elif app_type == ApplicationType.DETECTION.value:
            path = ApplicationSchemaFilePath.DETECTION
            self.driver.gui.mdl.vapp_schema_file = str(path)
            self.view.ids.schema_pick.select_path(str(path))

    def get_view(self) -> ConfigurationScreenView:
        return self.view

    def update_image_directory(self, path: str) -> None:
        assert self.driver.camera_state
        self.driver.camera_state.image_dir_path.value = Path(path)

    def update_inferences_directory(self, path: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.inference_dir_path.value = Path(path)

    def update_total_max_size(self, size: int) -> None:
        assert self.driver.camera_state
        self.driver.camera_state.total_dir_watcher.set_storage_limit(size)

    def apply_application_configuration(self) -> None:
        assert self.driver.camera_state

        try:
            if self.driver.camera_state.vapp_labels_file.value:
                self.driver.camera_state.vapp_labels_map.value = map_class_id_to_name(
                    Path(self.driver.camera_state.vapp_labels_file.value)
                )
        except FlatbufferError as e:
            self.view.display_error(str(e))

        if not self.driver.camera_state.vapp_config_file.value:
            return
        try:
            config = json.load(
                Path(self.driver.camera_state.vapp_config_file.value).open()
            )
            self.driver.from_sync(self.driver.send_app_config, json.dumps(config))
        except FileNotFoundError:
            self.view.display_error("App configuration does not exist")
        except ValueError:
            self.view.display_error("Error parsing app configuration JSON")
        except PermissionError:
            self.view.display_error("App configuration permission error")
        except Exception:
            self.view.display_error("App configuration unknown error")

    def apply_flatbuffers_schema(self) -> None:
        schema_file = self.driver.gui.mdl.vapp_schema_file
        if schema_file is not None and schema_file != "":
            if Path(schema_file).is_file():
                try:
                    assert self.driver.camera_state

                    conform_flatbuffer_schema(schema_file)
                    self.driver.camera_state.vapp_schema_file.value = schema_file
                    self.view.display_info("Success!")
                except FlatbufferError as e:
                    self.view.display_error(str(e))
            else:
                self.view.display_error("Not a file or file does not exist!")
        else:
            self.view.display_error("Please select a schema file.")

    def apply_configuration(self) -> None:
        self.apply_flatbuffers_schema()
        self.apply_application_configuration()
