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
from typing import Any

from kivymd.app import MDApp
from local_console.gui.enums import OTAUpdateStatus
from local_console.gui.schemas import OtaData
from local_console.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class FirmwareScreenView(BaseScreenView):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.app.mdl.bind(is_ready=self.app_state_refresh)

    def app_state_refresh(self, app: MDApp, value: bool) -> None:
        """
        Makes the update button react to the camera readiness state.
        """
        self.ids.btn_update_firmware.disabled = not self.app.mdl.is_ready

    def model_is_changed(self) -> None:
        self.ids.txt_firmware_file_version.text = self.model.firmware_file_version
        self.ids.txt_firmware_file_hash.text = self.model.firmware_file_hash
        self.ids.progress_downloading.value = self.model.downloading_progress
        self.ids.progress_updating.value = self.model.updating_progress
        self.ids.lbl_ota_status.text = self.model.update_status

        # If Done or Failed
        leaf_update_status = False

        if self.model.device_config:
            self.ids.txt_ota_data.text = OtaData(
                **self.model.device_config.model_dump()
            ).model_dump_json(indent=4)

            update_status = self.model.device_config.OTA.UpdateStatus
            leaf_update_status = update_status in (
                OTAUpdateStatus.DONE,
                OTAUpdateStatus.FAILED,
            )

        if self.model.firmware_file.is_file():
            self.ids.firmware_pick.accept_path(str(self.model.firmware_file))

        can_update = (
            self.app.mdl.is_ready
            and self.model.firmware_file_valid
            and leaf_update_status
            and self.model.firmware_file_version
        )
        self.ids.btn_update_firmware.disabled = not can_update
