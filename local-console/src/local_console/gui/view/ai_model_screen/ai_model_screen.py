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
from typing import Optional

from kivy.properties import BooleanProperty
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.camera_proxy import CameraStateProxy
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

    update_status_finished = BooleanProperty(False)

    def on_ai_model_file(self, proxy: CameraStateProxy, value: Optional[str]) -> None:
        if value and Path(value).is_file():
            self.ids.model_pick.accept_path(value)

    def on_ai_model_file_valid(self, proxy: CameraStateProxy, value: bool) -> None:
        if not value:
            self.display_error("Invalid AI Model file header!")

    def on_device_config(
        self, proxy: CameraStateProxy, value: Optional[DeviceConfiguration]
    ) -> None:
        # Restore default values
        self.update_status_finished = False
        self.ids.txt_ota_data.text = ""
        self.ids.lbl_ota_status.text = ""

        if value:
            self.ids.txt_ota_data.text = OtaData(**value.model_dump()).model_dump_json(
                indent=4
            )

            update_status = value.OTA.UpdateStatus
            self.update_status_finished = update_status in ("Done", "Failed")
            self.ids.lbl_ota_status.text = update_status

    @run_on_ui_thread
    def notify_deploy_timeout(self) -> None:
        self.display_error("Model deployment timed out!")
