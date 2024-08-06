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
from local_console.core.camera.qr import get_qr_object
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.connection_screen import ConnectionScreenModel
from local_console.gui.utils.qr import Color
from local_console.gui.utils.qr import qr_object_as_texture
from local_console.gui.utils.validators import validate_hostname
from local_console.gui.utils.validators import validate_ip_address
from local_console.gui.utils.validators import validate_port
from local_console.gui.view.connection_screen.connection_screen import (
    ConnectionScreenView,
)
from local_console.utils.local_network import replace_local_address


class ConnectionScreenController(BaseController):
    """
    The `ConnectionScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ConnectionScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = ConnectionScreenView(controller=self, model=self.model)

    def refresh(self) -> None:
        assert self.driver.device_manager
        # Delete previous QR code
        self.view.ids.img_qr_display.texture = None

        # Trigger for connection status
        proxy = self.driver.device_manager.get_active_device_proxy()
        state = self.driver.device_manager.get_active_device_state()
        assert state.is_connected.value is not None
        self.view.on_device_connection_update(proxy, state.is_connected.value)

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(is_connected=self.view.on_device_connection_update)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(is_connected=self.view.on_device_connection_update)

    def get_view(self) -> ConnectionScreenView:
        return self.view

    def set_mqtt_host(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.mqtt_host.value = value[
            : self.driver.camera_state.MAX_LEN_DOMAIN_NAME
        ]
        self.view.ids.txt_mqtt_host.text = self.driver.camera_state.mqtt_host.value

    def set_mqtt_port(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.mqtt_port.value = value[
            : self.driver.camera_state.MAX_LEN_PORT
        ]
        self.view.ids.txt_mqtt_port.text = self.driver.camera_state.mqtt_port.value

    def set_ntp_host(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.ntp_host.value = value[
            : self.driver.camera_state.MAX_LEN_DOMAIN_NAME
        ]
        self.view.ids.txt_ntp_host.text = self.driver.camera_state.ntp_host.value

    def set_ip_address(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.ip_address.value = value[
            : self.driver.camera_state.MAX_LEN_IP_ADDRESS
        ]
        self.view.ids.txt_ip_address.text = self.driver.camera_state.ip_address.value

    def set_subnet_mask(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.subnet_mask.value = value[
            : self.driver.camera_state.MAX_LEN_IP_ADDRESS
        ]
        self.view.ids.txt_subnet_mask.text = self.driver.camera_state.subnet_mask.value

    def set_gateway(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.gateway.value = value[
            : self.driver.camera_state.MAX_LEN_IP_ADDRESS
        ]
        self.view.ids.txt_gateway.text = self.driver.camera_state.gateway.value

    def set_dns_server(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.dns_server.value = value[
            : self.driver.camera_state.MAX_LEN_IP_ADDRESS
        ]
        self.view.ids.txt_dns_server.text = self.driver.camera_state.dns_server.value

    def set_wifi_ssid(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.wifi_ssid.value = value[
            : self.driver.camera_state.MAX_LEN_WIFI_SSID
        ]
        self.view.ids.txt_wifi_ssid.text = self.driver.camera_state.wifi_ssid.value

    def set_wifi_password(self, value: str) -> None:
        assert self.driver.camera_state

        self.driver.camera_state.wifi_password.value = value[
            : self.driver.camera_state.MAX_LEN_WIFI_PASSWORD
        ]
        self.view.ids.txt_wifi_password.text = (
            self.driver.camera_state.wifi_password.value
        )

    def validate_all_settings(self) -> bool:
        assert self.driver.camera_state

        warning_message = ""
        # Mandatory parameters
        if self.driver.camera_state.mqtt_host.value and validate_hostname(
            self.driver.camera_state.mqtt_host.value
        ):
            self.view.ids.txt_mqtt_host.error = False
        else:
            self.view.ids.txt_mqtt_host.error = True
            warning_message += "\n- MQTT host address"
        if self.driver.camera_state.mqtt_port.value and validate_port(
            self.driver.camera_state.mqtt_port.value
        ):
            self.view.ids.txt_mqtt_port.error = False
        else:
            self.view.ids.txt_mqtt_port.error = True
            warning_message += "\n- MQTT port"
        if self.driver.camera_state.ntp_host.value and validate_hostname(
            self.driver.camera_state.ntp_host.value
        ):
            self.view.ids.txt_ntp_host.error = False
        else:
            self.view.ids.txt_ntp_host.error = True
            warning_message += "\n- NTP server address"
        # Optional parameters
        if self.driver.camera_state.ip_address.value and not validate_ip_address(
            self.driver.camera_state.ip_address.value
        ):
            self.view.ids.txt_ip_address.error = True
            warning_message += "\n- IP Address"
        else:
            self.view.ids.txt_ip_address.error = False
        if self.driver.camera_state.subnet_mask.value and not validate_ip_address(
            self.driver.camera_state.subnet_mask.value
        ):
            self.view.ids.txt_subnet_mask.error = True
            warning_message += "\n- Subnet Mask"
        else:
            self.view.ids.txt_subnet_mask.error = False
        if self.driver.camera_state.gateway.value and not validate_ip_address(
            self.driver.camera_state.gateway.value
        ):
            self.view.ids.txt_gateway.error = True
            warning_message += "\n- Gateway"
        else:
            self.view.ids.txt_gateway.error = False
        if self.driver.camera_state.dns_server.value and not validate_ip_address(
            self.driver.camera_state.dns_server.value
        ):
            self.view.ids.txt_dns_server.error = True
            warning_message += "\n- DNS server"
        else:
            self.view.ids.txt_dns_server.error = False

        if warning_message != "":
            warning_message = "Warning, invalid parameters:" + warning_message
            self.view.display_error(warning_message)

        return warning_message == ""

    def qr_generate(self) -> None:
        # Get the local IP since it might be updated.
        if not self.validate_all_settings():
            return
        assert self.driver.camera_state

        # non-empty string
        assert self.driver.camera_state.mqtt_host.value
        assert self.driver.camera_state.mqtt_port.value
        assert self.driver.camera_state.ntp_host.value
        # not none or empty string
        assert self.driver.camera_state.ip_address.value is not None
        assert self.driver.camera_state.subnet_mask.value is not None
        assert self.driver.camera_state.gateway.value is not None
        assert self.driver.camera_state.dns_server.value is not None
        assert self.driver.camera_state.wifi_ssid.value is not None
        assert self.driver.camera_state.wifi_password.value is not None

        mqtt_port = (
            int(self.driver.camera_state.mqtt_port.value)
            if self.driver.camera_state.mqtt_port.value != ""
            else None
        )
        tls_enabled = False
        qr = get_qr_object(
            replace_local_address(self.driver.camera_state.mqtt_host.value),
            mqtt_port,
            tls_enabled,
            replace_local_address(self.driver.camera_state.ntp_host.value),
            self.driver.camera_state.ip_address.value,
            self.driver.camera_state.subnet_mask.value,
            self.driver.camera_state.gateway.value,
            self.driver.camera_state.dns_server.value,
            self.driver.camera_state.wifi_ssid.value,
            self.driver.camera_state.wifi_password.value,
            border=4,
        )
        background: Color = tuple(
            int(255 * (val * 1.1)) for val in self.view.theme_cls.backgroundColor[:3]
        )
        fill: Color = (0, 0, 0)
        self.view.ids.img_qr_display.texture = qr_object_as_texture(
            qr, background, fill
        )
