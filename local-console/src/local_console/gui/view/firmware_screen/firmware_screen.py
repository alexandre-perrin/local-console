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
from typing import Optional

from kivy.properties import BooleanProperty
from kivy.properties import NumericProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.firmware import TransientStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.enums import FirmwareType
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.model.data_binding import ViewTransientStatusBase
from local_console.gui.schemas import OtaData
from local_console.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class FirmwareTransientStatus(TransientStatus, ViewTransientStatusBase):
    update_status = StringProperty("")
    progress_download = NumericProperty(0)
    progress_update = NumericProperty(0)


class FirmwareScreenView(BaseScreenView):

    update_status_finished = BooleanProperty(False)
    transients = ObjectProperty(FirmwareTransientStatus, rebind=True)

    fw_type_ota_map = {
        FirmwareType.APPLICATION_FW: OTAUpdateModule.APFW,
        FirmwareType.SENSOR_FW: OTAUpdateModule.SENSORFW,
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.transients = FirmwareTransientStatus()
        self.transients.bind_widget_property(
            "progress_download", self.ids.progress_downloading, "value"
        )
        self.transients.bind_widget_property(
            "progress_update", self.ids.progress_updating, "value"
        )
        self.transients.bind_widget_property(
            "update_status", self.ids.lbl_ota_status, "text"
        )

    def map_ota_type(self, ota_type: OTAUpdateModule) -> FirmwareType:
        return {
            OTAUpdateModule.APFW: FirmwareType.APPLICATION_FW,
            OTAUpdateModule.SENSORFW: FirmwareType.SENSOR_FW,
        }[ota_type]

    def on_firmware_file(self, proxy: CameraStateProxy, value: Optional[str]) -> None:
        if value and Path(value).is_file():
            self.ids.firmware_pick.accept_path(value)

    def on_firmware_file_valid(self, proxy: CameraStateProxy, value: bool) -> None:
        if not value:
            firmware_file = Path(self.app.mdl.firmware_file)
            if firmware_file.suffix != FirmwareExtension.APPLICATION_FW:
                self.display_error("Invalid Application Firmware!")
            elif firmware_file.suffix != FirmwareExtension.SENSOR_FW:
                self.display_error("Invalid Sensor Firmware!")

    def on_device_config(
        self, proxy: CameraStateProxy, value: Optional[DeviceConfiguration]
    ) -> None:
        self.ids.txt_ota_data.text = ""
        self.transients.update_status = ""
        self.transients.progress_download = 0
        self.transients.progress_update = 0
        self.update_status_finished = False

        if value:
            self.ids.txt_ota_data.text = OtaData(**value.model_dump()).model_dump_json(
                indent=4
            )
            update_status = value.OTA.UpdateStatus
            self.update_status_finished = update_status in (
                OTAUpdateStatus.DONE,
                OTAUpdateStatus.FAILED,
            )
            self.transients.update_status = update_status
