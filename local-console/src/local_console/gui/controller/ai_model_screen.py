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
from typing import TYPE_CHECKING

from local_console.core.camera.ai_model import deployment_task
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.ai_model_screen import AIModelScreenModel

if TYPE_CHECKING:
    from local_console.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class AIModelScreenController(BaseController):
    """
    The `AIModelScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(
        self, model: AIModelScreenModel, driver: Driver, view: type["BaseScreenView"]
    ):
        self.model = model
        self.driver = driver
        self.view = view(controller=self, model=self.model)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(ai_model_file=self.view.on_ai_model_file)
        self.driver.gui.mdl.bind(ai_model_file_valid=self.view.on_ai_model_file_valid)
        self.driver.gui.mdl.bind(device_config=self.view.on_device_config)

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(ai_model_file=self.view.on_ai_model_file)
        self.driver.gui.mdl.unbind(ai_model_file_valid=self.view.on_ai_model_file_valid)
        self.driver.gui.mdl.unbind(device_config=self.view.on_device_config)

    def refresh(self) -> None:
        assert self.driver.camera_state
        self.view.on_device_config(
            self.driver.gui.mdl, self.driver.camera_state.device_config.value
        )

    def get_view(self) -> "BaseScreenView":
        return self.view

    def deploy(self) -> None:
        assert self.driver.camera_state

        self.driver.from_sync(
            deployment_task,
            self.driver.camera_state,
            self.driver.camera_state.ai_model_file.value,
            self.view.notify_deploy_timeout,
        )
