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
from importlib.metadata import version as version_info
from typing import Any
from typing import Optional

from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.view.base_screen import BaseScreenView


class HomeScreenView(BaseScreenView):
    version_number = f"Version: {version_info('local-console')}"

    def versions_refresh(
        self, proxy: CameraStateProxy, value: Optional[DeviceConfiguration]
    ) -> None:
        """
        Represent new state values
        """
        self.ids.txt_sensor_fw_ver.text = value.Version.SensorFwVersion if value else ""
        self.ids.txt_sensor_loader_ver.text = (
            value.Version.SensorLoaderVersion if value else ""
        )
        self.ids.txt_app_fw_ver.text = value.Version.ApFwVersion if value else ""
        self.ids.txt_app_loader_ver.text = (
            value.Version.ApLoaderVersion if value else ""
        )

    def on_enter(self, *args: Any) -> None:
        assert self.app.driver
        assert self.app.driver.device_manager

        dman = self.app.driver.device_manager
        self.ids.device_selector.populate_menu(dman.get_device_configs())
        self.app.switch_proxy()
