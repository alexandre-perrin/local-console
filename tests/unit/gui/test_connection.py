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
from tests.strategies.configs import generate_invalid_port_number
from tests.strategies.configs import generate_valid_ip
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
    assert not model.connected
    assert model.is_valid_parameters


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


@given(st.booleans())
def test_connected(connected: bool):
    with create_model() as model:
        model.connected = connected
