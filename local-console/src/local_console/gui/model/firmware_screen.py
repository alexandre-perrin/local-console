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

from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.enums import OTAUpdateModule
from local_console.gui.model.base_model import BaseScreenModel
from trio import Event

logger = logging.getLogger(__name__)


class FirmwareScreenModel(BaseScreenModel):
    """
    The Model for the Firmware screen.
    """

    def __init__(self) -> None:
        # These two variables enable signaling that the OTA
        # status has changed from a previous report
        self._ota_event = Event()
        self._device_config: DeviceConfiguration | None = None

        self._device_config_previous: DeviceConfiguration | None = None
        self._firmware_file = Path()
        self._firmware_file_valid = False
        self._firmware_file_type = OTAUpdateModule.APFW
        self._firmware_file_version = ""
        self._firmware_file_hash = ""
        self._downloading_progress = 0
        self._updating_progress = 0
        self._update_status = ""

    @property
    def device_config(self) -> DeviceConfiguration | None:
        return self._device_config

    @device_config.setter
    def device_config(self, value: DeviceConfiguration | None) -> None:
        self._device_config = value

        # detect content change
        if self._device_config_previous != value:
            self._device_config_previous = value
            self._ota_event.set()
            self.notify_observers()

    async def ota_event(self) -> None:
        self._ota_event = Event()
        await self._ota_event.wait()

    @property
    def firmware_file(self) -> Path:
        return self._firmware_file

    @firmware_file.setter
    def firmware_file(self, value: Path) -> None:
        self._firmware_file = value
        self.notify_observers()

    @property
    def firmware_file_valid(self) -> bool:
        return self._firmware_file_valid

    @firmware_file_valid.setter
    def firmware_file_valid(self, value: bool) -> None:
        self._firmware_file_valid = value
        self.notify_observers()

    @property
    def firmware_file_type(self) -> str:
        return self._firmware_file_type

    @firmware_file_type.setter
    def firmware_file_type(self, value: str) -> None:
        self._firmware_file_type = value
        self.notify_observers()

    @property
    def firmware_file_version(self) -> str:
        return self._firmware_file_version

    @firmware_file_version.setter
    def firmware_file_version(self, value: str) -> None:
        self._firmware_file_version = value
        self.notify_observers()

    @property
    def firmware_file_hash(self) -> str:
        return self._firmware_file_hash

    @firmware_file_hash.setter
    def firmware_file_hash(self, value: str) -> None:
        self._firmware_file_hash = value
        self.notify_observers()

    @property
    def downloading_progress(self) -> int:
        return self._downloading_progress

    @downloading_progress.setter
    def downloading_progress(self, value: int) -> None:
        self._downloading_progress = value
        self.notify_observers()

    @property
    def updating_progress(self) -> int:
        return self._updating_progress

    @updating_progress.setter
    def updating_progress(self, value: int) -> None:
        self._updating_progress = value
        self.notify_observers()

    @property
    def update_status(self) -> str:
        return self._update_status

    @update_status.setter
    def update_status(self, value: str) -> None:
        self._update_status = value
        self.notify_observers()
