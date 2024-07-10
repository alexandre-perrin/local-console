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
from typing import Any

from kivymd.app import MDApp
from local_console.gui.schemas import OtaData
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.view.base_screen import BaseScreenView
from local_console.gui.view.common.components import (
    CodeInputCustom,
)  # nopycln: import # Required by the screen's KV spec file
from local_console.gui.view.common.components import (
    PathSelectorCombo,
)  # nopycln: import # Required by the screen's KV spec file

logger = logging.getLogger(__name__)


class AIModelScreenView(BaseScreenView):
    def model_is_changed(self) -> None:

        can_deploy = (
            self.app.mdl.is_ready and self.model.model_file_valid and leaf_update_status
        )
        self.ids.btn_ota_file.disabled = not can_deploy

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.app.mdl.bind(ai_model_file=self.on_ai_model_file)
        self.app.mdl.bind(is_ready=self.app_state_refresh)
        self.app.mdl.bind(device_config=self.on_device_config)

    def on_ai_model_file(self, app: MDApp, value: Optional[str]) -> None:
        if value and Path(value).is_file():
            self.ids.model_pick.accept_path(value)

    def on_device_config(
        self, app: MDApp, value: Optional[DeviceConfiguration]
    ) -> None:
        if value:
            self.ids.txt_ota_data.text = OtaData(**value.model_dump()).model_dump_json(
                indent=4
            )

            update_status = value.OTA.UpdateStatus
            self.ids.lbl_ota_status.text = update_status
        if not self.model.model_file_valid:
            self.display_error("Invalid AI Model file header!")

    def app_state_refresh(self, app: MDApp, value: bool) -> None:
        """
        Makes the deploy button react to the camera readiness state.
        """
        self.ids.btn_ota_file.disabled = not self.app.mdl.is_ready

    @run_on_ui_thread
    def notify_deploy_timeout(self) -> None:
        self.display_error("Model deployment timed out!")
