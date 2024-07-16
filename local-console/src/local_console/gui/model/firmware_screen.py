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
from local_console.gui.model.base_model import BaseScreenModel

logger = logging.getLogger(__name__)


class FirmwareScreenModel(BaseScreenModel):
    """
    The Model for the Firmware screen.
    """

    def __init__(self) -> None:
        self._downloading_progress = 0
        self._updating_progress = 0
        self._update_status = ""

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
