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
import pytest
import trio
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from local_console.core.config import config_obj
from local_console.gui.controller.connection_screen import ConnectionScreenController

from tests.fixtures.camera import cs_init
from tests.fixtures.camera import cs_init_context
from tests.fixtures.gui import driver_context
from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_random_characters
from tests.strategies.configs import generate_valid_port_number


@pytest.mark.trio
async def test_initialization(cs_init) -> None:
    with driver_context() as (driver, _):
        driver.camera_state = cs_init
        device = config_obj.get_active_device_config()
        driver.camera_state.initialize_connection_variables("EVP1", device)
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            ConnectionScreenController(Mock(), driver)

            assert driver.camera_state.mqtt_host.value == str(device.mqtt.host)
            assert driver.camera_state.mqtt_port.value == device.mqtt.port
            assert driver.camera_state.ntp_host.value == "pool.ntp.org"
            assert driver.camera_state.ip_address.value == ""
            assert driver.camera_state.subnet_mask.value == ""
            assert driver.camera_state.gateway.value == ""
            assert driver.camera_state.dns_server.value == ""
            assert driver.camera_state.wifi_ssid.value == ""
            assert driver.camera_state.wifi_password.value == ""

            assert not driver.camera_state.is_connected.value


# local_ip


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_local_ip_valid_update(ip: str):
    with driver_context() as (driver, _):
        with (
            patch(
                "local_console.gui.controller.connection_screen.ConnectionScreenView"
            ),
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # validate ip
                assert ctrl.validate_all_settings()
                nursery.cancel_scope.cancel()


# mqtt_host


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_mqtt_host_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                config = config_obj.get_config()
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables(
                    config.evp.iot_platform, device
                )
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_mqtt_host(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_mqtt_host_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_mqtt_host(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- MQTT host address"
                )
                nursery.cancel_scope.cancel()


# mqtt_port


@pytest.mark.trio
@given(port=generate_valid_port_number())
async def test_mqtt_port_valid_update(port: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_mqtt_port(str(port))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_mqtt_port_invalid_update(cs_init) -> None:
    port = -1
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            driver.camera_state = cs_init
            device = config_obj.get_active_device_config()
            driver.camera_state.initialize_connection_variables("EVP1", device)
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
@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_ntp_host_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_ntp_host(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_ntp_host_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_ntp_host(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- NTP server address"
                )
                nursery.cancel_scope.cancel()


# ip_address


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_ip_address_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_ip_address(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_ip_address_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_ip_address(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- IP Address"
                )
                nursery.cancel_scope.cancel()


# subnet_mask


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_subnet_mask_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_subnet_mask(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_subnet_mask_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_subnet_mask(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- Subnet Mask"
                )
                nursery.cancel_scope.cancel()


# gateway


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_gateway_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_gateway(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_gateway_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_gateway(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- Gateway"
                )
                nursery.cancel_scope.cancel()


# dns_server


@pytest.mark.trio
@given(ip=st.ip_addresses(v=4))
async def test_dns_server_valid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_dns_server(str(ip))
                # validate ip
                assert ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_info.assert_not_called()
                nursery.cancel_scope.cancel()


@settings(deadline=1000)
@pytest.mark.trio
@given(ip=generate_invalid_ip())
async def test_dns_server_invalid_update(ip: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
                ctrl = ConnectionScreenController(Mock(), driver)
                # reset ip
                ctrl.set_dns_server(str(ip))
                # validate ip
                assert not ctrl.validate_all_settings()
                # check warning raised if changed
                ctrl.view.display_error.assert_called_once_with(
                    "Warning, invalid parameters:\n- DNS server"
                )
                nursery.cancel_scope.cancel()


# wifi_ssid / wifi_password


@pytest.mark.trio
@given(
    generate_random_characters(min_size=33, max_size=35),
    generate_random_characters(min_size=33, max_size=35),
)
async def test_wifi_ssid_password_long(ssid: str, password: str):
    with driver_context() as (driver, _):
        with patch(
            "local_console.gui.controller.connection_screen.ConnectionScreenView"
        ):
            async with (
                trio.open_nursery() as nursery,
                cs_init_context() as camera,
            ):
                driver.camera_state = camera
                device = config_obj.get_active_device_config()
                driver.camera_state.initialize_connection_variables("EVP1", device)
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
                nursery.cancel_scope.cancel()
