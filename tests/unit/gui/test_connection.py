from contextlib import contextmanager
from unittest.mock import patch

import hypothesis.strategies as st
from hypothesis import given
from pytest import fixture
from wedge_cli.core.config import config_to_schema
from wedge_cli.core.config import get_default_config
from wedge_cli.gui.model.connection_screen import ConnectionScreenModel
from wedge_cli.gui.utils.observer import Observer

from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_invalid_ip_long
from tests.strategies.configs import generate_invalid_port_number
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_ip_strict
from tests.strategies.configs import generate_valid_port_number


def mock_get_config():
    return config_to_schema(get_default_config())


@fixture(autouse=True)
def fixture_get_config():
    with patch(
        "wedge_cli.gui.model.connection_screen.get_config",
        mock_get_config,
    ) as _fixture:
        yield _fixture


class ModelObserver(Observer):
    def __init__(self):
        self.is_called = False

    def model_is_changed(self) -> None:
        self.is_called = True


@contextmanager
def create_model() -> ConnectionScreenModel:
    model = ConnectionScreenModel()
    observer = ModelObserver()
    model.add_observer(observer)
    yield model
    assert observer.is_called


def test_initialization():
    model = ConnectionScreenModel()
    assert model.mqtt_host == mock_get_config().mqtt.host.ip_value
    assert model.mqtt_host_valid
    assert model.mqtt_port == f"{mock_get_config().mqtt.port}"
    assert model.mqtt_port_valid
    assert model.ntp_host_valid
    assert model.ip_address == ""
    assert model.subnet_mask == ""
    assert model.subnet_mask_valid
    assert model.gateway == ""
    assert model.dns_server == ""
    assert not model.connected
    assert not model.local_ip_updated
    assert model.is_valid_parameters


# local ip
@given(generate_valid_ip())
def test_local_ip(valid_ip: str):
    with create_model() as model:
        model.local_ip = valid_ip
        assert model.local_ip_updated
        model.local_ip_updated = False
        model.local_ip = valid_ip
        assert not model.local_ip_updated


@given(generate_invalid_ip())
def test_local_ip(invalid_ip: str):
    with create_model() as model:
        model.local_ip = invalid_ip
        assert model.local_ip_updated
        model.local_ip_updated = False
        model.local_ip = invalid_ip
        assert not model.local_ip_updated


# mqtt host
@given(generate_valid_ip())
def test_mqtt_host(valid_ip: str):
    with create_model() as model:
        model.mqtt_host = valid_ip
        assert model.mqtt_host_valid
        assert model.is_valid_parameters


@given(generate_invalid_ip())
def test_mqtt_host_invalid(invalid_ip: str):
    with create_model() as model:
        model.mqtt_host = invalid_ip
        assert not model.mqtt_host_valid
        assert not model.is_valid_parameters


# ntp host
@given(generate_valid_ip())
def test_ntp_host(valid_ip: str):
    with create_model() as model:
        model.ntp_host = valid_ip
        assert model.ntp_host_valid
        assert model.is_valid_parameters


@given(generate_invalid_ip())
def test_ntp_host_invalid(invalid_ip: str):
    with create_model() as model:
        model.ntp_host = invalid_ip
        assert not model.ntp_host_valid
        assert not model.is_valid_parameters


# mqtt port
@given(generate_valid_port_number())
def test_mqtt_port(port: int):
    with create_model() as model:
        model.mqtt_port = port
        assert model.mqtt_port_valid
        assert model.is_valid_parameters


@given(generate_invalid_port_number())
def test_mqtt_port_invalid(port: int):
    with create_model() as model:
        model.mqtt_port = port
        assert not model.mqtt_port_valid
        assert not model.is_valid_parameters


# ip address
@given(generate_valid_ip())
def test_ip_address(ip: str):
    with create_model() as model:
        model.ip_address = ip
        assert len(model.ip_address) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip())
def test_ip_address_invalid(ip: str):
    with create_model() as model:
        model.ip_address = ip
        assert len(model.ip_address) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip_long())
def test_ip_address_invalid_long(ip: str):
    with create_model() as model:
        model.ip_address = ip
        assert len(model.ip_address) <= model.MAX_STRING_LENGTH


# subnet mask
@given(generate_valid_ip_strict())
def test_subnet_mask(ip: str):
    with create_model() as model:
        model.subnet_mask = ip
        assert model.subnet_mask_valid
        assert model.is_valid_parameters
        assert len(model.subnet_mask) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip())
def test_subnet_mask_invalid(ip: str):
    with create_model() as model:
        model.subnet_mask = ip
        assert not model.subnet_mask_valid
        assert not model.is_valid_parameters
        assert len(model.subnet_mask) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip_long())
def test_subnet_mask_invalid_long(ip: str):
    with create_model() as model:
        model.subnet_mask = ip
        assert not model.subnet_mask_valid
        assert not model.is_valid_parameters
        assert len(model.subnet_mask) <= model.MAX_STRING_LENGTH


# gateway
@given(generate_valid_ip())
def test_gateway(ip: str):
    with create_model() as model:
        model.gateway = ip
        assert len(model.gateway) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip())
def test_gateway_invalid(ip: str):
    with create_model() as model:
        model.gateway = ip
        assert len(model.gateway) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip_long())
def test_gateway_invalid_long(ip: str):
    with create_model() as model:
        model.gateway = ip
        assert len(model.gateway) <= model.MAX_STRING_LENGTH


# dns_server
@given(generate_valid_ip())
def test_dns_server(ip: str):
    with create_model() as model:
        model.dns_server = ip
        assert len(model.dns_server) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip())
def test_dns_server_invalid(ip: str):
    with create_model() as model:
        model.dns_server = ip
        assert len(model.dns_server) <= model.MAX_STRING_LENGTH


@given(generate_invalid_ip_long())
def test_dns_server_invalid_long(ip: str):
    with create_model() as model:
        model.dns_server = ip
        assert len(model.dns_server) <= model.MAX_STRING_LENGTH


# connection status
@given(st.booleans())
def test_connected(connected: bool):
    with create_model() as model:
        model.connected = connected
