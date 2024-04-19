from base64 import b64encode
from unittest.mock import patch

import hypothesis.strategies as st
from hypothesis import given
from wedge_cli.core.camera import Camera
from wedge_cli.core.camera import get_qr_object
from wedge_cli.core.camera import qr_string
from wedge_cli.core.camera import StreamStatus
from wedge_cli.core.schemas.edge_cloud_if_v1 import DeviceConfiguration

from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_invalid_port_number
from tests.strategies.configs import generate_valid_device_configuration
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
    st.integers(min_value=-1, max_value=100),
)
def test_get_qr_object(
    ip: str,
    port: str,
    tls_enabled: bool,
    border: int,
) -> None:
    with patch("wedge_cli.core.camera.qr_string", return_value="") as mock_qr_string:
        qr_code = get_qr_object(
            mqtt_host=ip,
            mqtt_port=port,
            tls_enabled=tls_enabled,
            ntp_server=ip,
            ip_address=ip,
            subnet_mask=ip,
            gateway=ip,
            dns_server=ip,
            border=border,
        )
        assert qr_code is not None

        mock_qr_string.assert_called_once_with(
            ip,
            port,
            tls_enabled,
            ip,
            ip,
            ip,
            ip,
            ip,
        )


@given(
    generate_invalid_ip(),
    generate_invalid_port_number(),
    st.booleans(),
    st.integers(min_value=-1, max_value=100),
)
def test_get_qr_object_invalid(
    ip: str,
    port: str,
    tls_enabled: bool,
    border: int,
) -> None:
    with patch("wedge_cli.core.camera.qr_string", return_value="") as mock_qr_string:
        qr_code = get_qr_object(
            mqtt_host=ip,
            mqtt_port=port,
            tls_enabled=tls_enabled,
            ntp_server=ip,
            ip_address=ip,
            subnet_mask=ip,
            gateway=ip,
            dns_server=ip,
            border=border,
        )
        assert qr_code is not None

        mock_qr_string.assert_called_once_with(
            ip,
            port,
            tls_enabled,
            ip,
            ip,
            ip,
            ip,
            ip,
        )


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
)
def test_get_qr_string(
    ip: str,
    port: str,
    tls_enabled: bool,
) -> None:
    output = qr_string(
        mqtt_host=ip,
        mqtt_port=port,
        tls_enabled=tls_enabled,
        ntp_server=ip,
        ip_address=ip,
        subnet_mask=ip,
        gateway=ip,
        dns_server=ip,
    )

    tls_flag = 0 if tls_enabled else 1
    assert (
        output
        == f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={ip};H={port};t={tls_flag};I={ip};K={ip};G={ip};D={ip};T={ip};U1FS"
    )


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
)
def test_get_qr_string_no_static_ip(
    ip: str,
    port: str,
    tls_enabled: bool,
) -> None:
    output = qr_string(
        mqtt_host=ip,
        mqtt_port=port,
        tls_enabled=tls_enabled,
        ntp_server=ip,
    )

    tls_flag = 0 if tls_enabled else 1
    assert (
        output
        == f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={ip};H={port};t={tls_flag};T={ip};U1FS"
    )


@given(generate_valid_device_configuration())
def test_process_state_topic(device_config: DeviceConfiguration) -> None:
    camera = Camera()
    assert not camera.is_new_device_config
    assert camera.device_config is None
    backdoor_state = {
        "state/backdoor-EA_Main/placeholder": b64encode(
            device_config.model_dump_json().encode("utf-8")
        ).decode("utf-8")
    }
    camera.process_state_topic(backdoor_state)
    assert camera.is_new_device_config
    assert not camera.is_new_device_config
    assert camera.device_config == device_config
    assert camera.sensor_state == StreamStatus.from_string(device_config.Status.Sensor)
