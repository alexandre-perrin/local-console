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
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.base_model import BaseScreenModel


class HomeScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.home_screen.HomeScreen.HomeScreenView` class.
    """

    def __init__(self) -> None:
        self._device_config: DeviceConfiguration | None = None
        self._sensor_fw_ver: str = ""
        self._sensor_loader_ver: str = ""
        self._app_fw_ver: str = ""
        self._app_loader_ver: str = ""

    @property
    def device_config(self) -> DeviceConfiguration | None:
        return self._device_config

    @device_config.setter
    def device_config(self, value: DeviceConfiguration | None) -> None:
        self._device_config = value
        if value:
            self._sensor_fw_ver = value.Version.SensorFwVersion
            self._sensor_loader_ver = value.Version.SensorLoaderVersion
            self._app_fw_ver = value.Version.ApFwVersion
            self._app_loader_ver = value.Version.ApLoaderVersion
            self.notify_observers()

    @property
    def sensor_fw_ver(self) -> str:
        return self._sensor_fw_ver

    @property
    def sensor_loader_ver(self) -> str:
        return self._sensor_loader_ver

    @property
    def app_fw_ver(self) -> str:
        return self._app_fw_ver

    @property
    def app_loader_ver(self) -> str:
        return self._app_loader_ver
