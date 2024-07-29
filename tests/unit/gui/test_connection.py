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
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
from hypothesis import given
from hypothesis import strategies as st
from local_console.gui.controller.connection_screen import ConnectionScreenController
from local_console.gui.utils.validators import validate_ip_address
from local_console.utils.local_network import get_my_ip_by_routing
from pytest import mark

from tests.fixtures.gui import driver_context
from tests.fixtures.gui import get_default_config_as_schema
from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_random_characters
from tests.strategies.configs import generate_valid_port_number


def test_initialization():
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ConnectionScreenController(Mock(), driver)

            config = get_default_config_as_schema()
            assert driver.camera_state.local_ip.value == get_my_ip_by_routing()
            assert driver.camera_state.mqtt_host.value == str(config.mqtt.host)
            assert driver.camera_state.mqtt_port.value == str(config.mqtt.port)
            assert driver.camera_state.ntp_host.value == "pool.ntp.org"
            assert driver.camera_state.ip_address.value == ""
            assert driver.camera_state.subnet_mask.value == ""
            assert driver.camera_state.gateway.value == ""
            assert driver.camera_state.dns_server.value == ""
            assert driver.camera_state.wifi_ssid.value == ""
            assert driver.camera_state.wifi_password.value == ""
            assert driver.camera_state.wifi_password_hidden.value is True
            assert driver.camera_state.wifi_icon_eye.value == "eye-off"

            assert not driver.camera_state.is_connected.value


# local_ip


@given(ip=st.ip_addresses(v=4))
def test_local_ip_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            driver.camera_state.local_ip.value = ""
            ctrl.set_ip_address(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()
            ctrl.refresh_local_ip()
            ctrl.view.display_info.assert_called_once_with(
                "Warning, Local IP Address is updated."
            )


@given(ip=generate_invalid_ip())
def test_local_ip_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            driver.camera_state.local_ip.value = ""
            ctrl.set_ip_address(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()


# List of addresses to check
addresses_to_check = [
    "1.2.3.4.5",  # DTSS-25
    "1A.2B.3C.4D.5C",  # DTSS-26
    "123.345.567.789",  # DTSS-44
    "!@#$%^^",  # DTSS-45
    "AB1.CD2.ED3.GH4",  # DTSS-47
]


@mark.parametrize("ip", addresses_to_check)
def test_local_ip_invalid_update_from_list(ip: str):
    with driver_context() as (driver, _):
        with (
            patch(
                "local_console.gui.controller.connection_screen.ConnectionScreenView"
            ),
            patch(
                "local_console.gui.controller.connection_screen.get_my_ip_by_routing",
                return_value="",
            ),
        ):
            ConnectionScreenController(Mock(), driver)
            assert not validate_ip_address(ip)


def test_local_ip_empty():
    with driver_context() as (driver, _):
        with (
            patch(
                "local_console.gui.controller.connection_screen.ConnectionScreenView"
            ),
            patch(
                "local_console.gui.controller.connection_screen.get_my_ip_by_routing",
                return_value="",
            ),
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            driver.camera_state.local_ip.value = ""
            # validate ip
            assert ctrl.validate_all_settings()
            ctrl.refresh_local_ip()
            ctrl.view.display_info.assert_called_once_with(
                "Warning, No Local IP Address.\nPlease check connectivity."
            )


# mqtt_host


@given(ip=st.ip_addresses(v=4))
def test_mqtt_host_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_mqtt_host(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_mqtt_host_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_mqtt_host(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- MQTT host address"
            )


# mqtt_port


@given(port=generate_valid_port_number())
def test_mqtt_port_valid_update(port: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_mqtt_port(str(port))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


def test_mqtt_port_invalid_update():
    port = -1
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_mqtt_port(str(port))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- MQTT port"
            )


# ntp_host


@given(ip=st.ip_addresses(v=4))
def test_ntp_host_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_ntp_host(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_ntp_host_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_ntp_host(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- NTP server address"
            )


# ip_address


@given(ip=st.ip_addresses(v=4))
def test_ip_address_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_ip_address(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_ip_address_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_ip_address(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- IP Address"
            )


# subnet_mask


@given(ip=st.ip_addresses(v=4))
def test_subnet_mask_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_subnet_mask(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_subnet_mask_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_subnet_mask(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- Subnet Mask"
            )


# gateway


@given(ip=st.ip_addresses(v=4))
def test_gateway_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_gateway(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_gateway_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_gateway(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- Gateway"
            )


# dns_server


@given(ip=st.ip_addresses(v=4))
def test_dns_server_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_dns_server(str(ip))
            # validate ip
            assert ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_info.assert_not_called()


@given(ip=generate_invalid_ip())
def test_dns_server_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            # reset ip
            ctrl.set_dns_server(str(ip))
            # validate ip
            assert not ctrl.validate_all_settings()
            # check warning raised if changed
            ctrl.view.display_error.assert_called_once_with(
                "Warning, invalid parameters:\n- DNS server"
            )


# wifi_ssid / wifi_password


def test_wifi_password_toggle():
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            assert driver.camera_state.wifi_password_hidden.value
            assert driver.camera_state.wifi_icon_eye.value == "eye-off"
            ctrl.toggle_password_visible()
            assert not driver.camera_state.wifi_password_hidden.value
            assert driver.camera_state.wifi_icon_eye.value == "eye"


@given(
    generate_random_characters(min_size=33, max_size=35),
    generate_random_characters(min_size=33, max_size=35),
)
def test_wifi_ssid_password_long(ssid: str, password: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ctrl = ConnectionScreenController(Mock(), driver)
            ctrl.set_wifi_ssid(str(ssid))
            assert (
                driver.camera_state.wifi_ssid.value
                == ssid[: driver.camera_state.MAX_LEN_WIFI_SSID]
            )
            ctrl.set_wifi_password(password)
            assert (
                driver.camera_state.wifi_password.value
                == password[: driver.camera_state.MAX_LEN_WIFI_PASSWORD]
            )
