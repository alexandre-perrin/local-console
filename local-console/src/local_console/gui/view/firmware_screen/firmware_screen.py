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

from local_console.core.camera import OTAUpdateStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.schemas import OtaData
from local_console.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class FirmwareScreenView(BaseScreenView):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.app.mdl.bind(device_config=self.on_device_config)
    def model_is_changed(self) -> None:
        self.ids.progress_downloading.value = self.model.downloading_progress
        self.ids.progress_updating.value = self.model.updating_progress
        self.ids.lbl_ota_status.text = self.model.update_status



    def on_device_config(
        self, proxy: CameraStateProxy, value: Optional[DeviceConfiguration]
    ) -> None:
        update_status_finished = False
        if value:
            self.ids.txt_ota_data.text = OtaData(**value.model_dump()).model_dump_json(
                indent=4
            )
            update_status = value.OTA.UpdateStatus
            update_status_finished = update_status in (
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
