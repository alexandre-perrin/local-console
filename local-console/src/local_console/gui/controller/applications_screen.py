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
import logging
from pathlib import Path

from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.applications_screen import ApplicationsScreenModel
from local_console.gui.view.applications_screen.applications_screen import (
    ApplicationsScreenView,
)
from local_console.utils.validation import validate_app_file


logger = logging.getLogger(__name__)


class ApplicationsScreenController(BaseController):
    """
    The `ApplicationsScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ApplicationsScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = ApplicationsScreenView(controller=self, model=self.model)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(deploy_stage=self.view.on_deploy_stage)

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(deploy_stage=self.view.on_deploy_stage)

    def refresh(self) -> None:
        assert self.driver.camera_state
        if self.driver.camera_state.module_file.value is not None:
            self.view.app_file_valid = validate_app_file(
                Path(self.driver.camera_state.module_file.value)
            )
        self.view.on_deploy_stage(
            self.driver.gui.mdl, self.driver.camera_state.deploy_stage.value
        )

    def get_view(self) -> ApplicationsScreenView:
        return self.view

    def deploy(self) -> None:
        self.driver.do_app_deployment()
