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

from local_console.core.camera.firmware import update_firmware_task
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.firmware_screen import FirmwareScreenModel
from local_console.gui.view.firmware_screen.firmware_screen import FirmwareScreenView

logger = logging.getLogger(__name__)


class FirmwareScreenController(BaseController):
    """
    The `FirmwareScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: FirmwareScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = FirmwareScreenView(controller=self, model=self.model)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(device_config=self.view.on_device_config)
        self.driver.gui.mdl.bind(firmware_file=self.view.on_firmware_file)
        self.driver.gui.mdl.bind(firmware_file_valid=self.view.on_firmware_file_valid)

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(device_config=self.view.on_device_config)
        self.driver.gui.mdl.unbind(firmware_file=self.view.on_firmware_file)
        self.driver.gui.mdl.unbind(firmware_file_valid=self.view.on_firmware_file_valid)

    def refresh(self) -> None:
        assert self.driver.camera_state
        self.view.on_device_config(
            self.driver.gui.mdl, self.driver.camera_state.device_config.value
        )

    def get_view(self) -> FirmwareScreenView:
        return self.view

    def update_firmware(self) -> None:
        """
        Called when an user clicks the "Update" button.
        """
        self.driver.from_sync(
            update_firmware_task,
            self.driver.camera_state,
            self.view.transients,
            self.view.display_error,
        )
