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

from local_console.core.config import add_device_to_config
from local_console.core.config import get_device_configs
from local_console.core.config import remove_device_config
from local_console.core.schemas.schemas import DeviceListItem

logger = logging.getLogger(__name__)


class DeviceManager:
    def add_device(self, device: DeviceListItem) -> None:
        add_device_to_config(device)

    def remove_device(self, name: str) -> None:
        remove_device_config(name)

    def get_device_config(self) -> list[DeviceListItem]:
        device_configs = get_device_configs()
        return device_configs

    def set_active_device(self, name: str) -> None:
        """
        This is the function to set active device.
        To be implemented for handling multiple devices.
        """
