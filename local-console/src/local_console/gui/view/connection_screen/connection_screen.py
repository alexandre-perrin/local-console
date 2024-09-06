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
from typing import Optional

from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.view.base_screen import BaseScreenView
from local_console.gui.view.common.components import (
    FocusText,
)  # nopycln: import # Required by the screen's KV spec file
from local_console.gui.view.common.components import (
    GUITooltip,
)
from local_console.utils.local_network import get_mqtt_ip

logger = logging.getLogger(__name__)


class LocalIPInput(GUITooltip, FocusText):
    pass


class ConnectionScreenView(BaseScreenView):

    INPUTBOX_HEIGHT = "32dp"

    def on_enter(self) -> None:
        ip = get_mqtt_ip()
        self.ids.lbl_local_ip.text = ip
        if ip == "":
            # In case of no connectivity
            self.view.display_info(
                "Warning, No Local IP Address.\nPlease check connectivity."
            )

    def on_device_connection_update(
        self, proxy: CameraStateProxy, value: Optional[bool]
    ) -> None:
        self.ids.lbl_conn_status.text = (
            "Connected [No TLS]" if value else "Disconnected"
        )

    def on_password_hide_update(
        self, proxy: CameraStateProxy, value: Optional[bool]
    ) -> None:
        self.ids.txt_wifi_password.password = value

    def toggle_password_visible(self) -> None:
        toggled = not self.ids.txt_wifi_password.password
        self.ids.txt_wifi_password.password = toggled
        self.ids.btn_icon_eye.icon = "eye-off" if toggled else "eye"
