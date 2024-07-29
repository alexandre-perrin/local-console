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
import json
from base64 import b64encode
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
from hypothesis import given
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.qr import get_qr_object
from local_console.core.camera.qr import qr_string
from local_console.core.camera.state import CameraState
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol

from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_invalid_port_number
from tests.strategies.configs import generate_random_characters
from tests.strategies.configs import generate_valid_device_configuration
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number
from tests.unit.core.test_deploy import template_deploy_status_for_manifest


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
    st.integers(min_value=-1, max_value=100),
    generate_random_characters(min_size=1, max_size=32),
)
def test_get_qr_object(
    ip: str,
    port: str,
    tls_enabled: bool,
    border: int,
    text: str,
) -> None:
    with patch(
        "local_console.core.camera.qr.qr_string", return_value=""
    ) as mock_qr_string:
        qr_code = get_qr_object(
            mqtt_host=ip,
            mqtt_port=port,
            tls_enabled=tls_enabled,
            ntp_server=ip,
            ip_address=ip,
            subnet_mask=ip,
            gateway=ip,
            dns_server=ip,
            wifi_ssid=text,
            wifi_password=text,
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
            text,
            text,
        )


@given(
    generate_invalid_ip(),
    generate_invalid_port_number(),
    st.booleans(),
    st.integers(min_value=-1, max_value=100),
    generate_random_characters(min_size=1, max_size=32),
)
def test_get_qr_object_invalid(
    ip: str,
    port: str,
    tls_enabled: bool,
    border: int,
    text: str,
) -> None:
    with patch(
        "local_console.core.camera.qr.qr_string", return_value=""
    ) as mock_qr_string:
        qr_code = get_qr_object(
            mqtt_host=ip,
            mqtt_port=port,
            tls_enabled=tls_enabled,
            ntp_server=ip,
            ip_address=ip,
            subnet_mask=ip,
            gateway=ip,
            dns_server=ip,
            wifi_ssid=text,
            wifi_password=text,
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
            text,
            text,
        )


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
    generate_random_characters(min_size=1, max_size=32),
)
def test_get_qr_string(
    ip: str,
    port: str,
    tls_enabled: bool,
    text: str,
) -> None:
    output = qr_string(
        mqtt_host=ip,
        mqtt_port=port,
        tls_enabled=tls_enabled,
        ntp_server=ip,
        ip_address=ip,
        subnet_mask=ip,
        gateway=ip,
        wifi_ssid=text,
        wifi_password=text,
        dns_server=ip,
    )

    tls_flag = 0 if tls_enabled else 1
    assert (
        output
        == f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={ip};H={port};t={tls_flag};S={text};P={text};I={ip};K={ip};G={ip};D={ip};T={ip};U1FS"
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


@pytest.mark.trio
@given(generate_valid_device_configuration())
async def test_process_state_topic_correct(device_config: DeviceConfiguration) -> None:
    observer = AsyncMock()
    camera = CameraState()
    camera.device_config.subscribe_async(observer)
    observer.assert_not_awaited()

    backdoor_state = {
        "state/backdoor-EA_Main/placeholder": b64encode(
            device_config.model_dump_json().encode("utf-8")
        ).decode("utf-8")
    }
    await camera._process_state_topic(backdoor_state)

    observer.assert_awaited_once_with(device_config, None)
    assert camera.device_config.value == device_config
    assert camera.stream_status.value == StreamStatus.from_string(
        device_config.Status.Sensor
    )


@pytest.mark.trio
async def test_process_state_topic_wrong(caplog) -> None:
    camera = CameraState()

    wrong_obj = {"a": "b"}
    backdoor_state = {
        "state/backdoor-EA_Main/placeholder": b64encode(json.dumps(wrong_obj).encode())
    }
    await camera._process_state_topic(backdoor_state)
    assert "Error while validating device configuration" in caplog.text


@pytest.mark.trio
@given(st.sampled_from(OnWireProtocol))
async def test_process_systeminfo(proto_spec: OnWireProtocol) -> None:
    camera = CameraState()

    sysinfo_report = {"systemInfo": {"protocolVersion": str(proto_spec)}}
    await camera._process_sysinfo_topic(sysinfo_report)

    assert camera.attributes_available
    assert camera._onwire_schema == proto_spec


@pytest.mark.trio
async def test_process_deploy_status_evp1() -> None:
    camera = CameraState()
    camera._onwire_schema = OnWireProtocol.EVP1
    dummy_deployment = {"a": "b"}

    status_report = {"deploymentStatus": json.dumps(dummy_deployment)}
    await camera._process_deploy_status_topic(status_report)

    assert camera.deploy_status.value == dummy_deployment
    assert camera.attributes_available


@pytest.mark.trio
async def test_process_deploy_status_evp2() -> None:
    camera = CameraState()
    camera._onwire_schema = OnWireProtocol.EVP2
    dummy_deployment = {"a": "b"}

    status_report = {"deploymentStatus": dummy_deployment}
    await camera._process_deploy_status_topic(status_report)

    assert camera.deploy_status.value == dummy_deployment
    assert camera.attributes_available


@pytest.mark.trio
async def test_process_incoming_telemetry() -> None:
    with patch("local_console.core.camera.state.datetime") as mock_time:
        mock_now = Mock()
        mock_time.now.return_value = mock_now

        camera = CameraState()
        dummy_telemetry = {"a": "b"}
        await camera.process_incoming("v1/devices/me/telemetry", dummy_telemetry)

        assert camera._last_reception == mock_now


@pytest.mark.trio
@pytest.mark.parametrize(
    "topic, function",
    [
        (CameraState.EA_STATE_TOPIC, "_process_state_topic"),
        (CameraState.SYSINFO_TOPIC, "_process_sysinfo_topic"),
        (CameraState.DEPLOY_STATUS_TOPIC, "_process_deploy_status_topic"),
    ],
)
async def test_process_incoming(topic, function) -> None:
    camera = CameraState()
    with (patch.object(camera, function) as mock_proc,):
        payload = {topic: {"a": "b"}}
        await camera.process_incoming(MQTTTopics.ATTRIBUTES.value, payload)
        mock_proc.assert_awaited_once_with(payload)


@pytest.mark.trio
async def test_process_deploy_fsm_evp2_happy(nursery, tmp_path) -> None:
    camera = CameraState()

    # setup for parsing deployment status messages
    camera._onwire_schema = OnWireProtocol.EVP2
    wrap_dep_sta = lambda dep_sta: {"deploymentStatus": dep_sta}

    # Dummy module to deploy
    module = tmp_path / "module"
    module.touch()

    # async setup
    with (
        patch("local_console.core.commands.deploy.SyncWebserver"),
        patch("local_console.core.camera.state.Agent") as mock_agent,
    ):
        camera.set_nursery(nursery)
        mock_agent.onwire_schema = camera._onwire_schema
        mock_agent.deploy = AsyncMock()

        # initial state
        assert camera.deploy_operation.value is None
        assert camera.deploy_stage.value is None

        # trigger deployment
        camera.module_file.value = module
        await camera.do_app_deployment(mock_agent)
        assert camera.deploy_operation.value == DeploymentType.Application
        assert camera.deploy_stage.value == DeployStage.WaitFirstStatus
        dep_sta_tpl = template_deploy_status_for_manifest(camera._deploy_fsm._to_deploy)

        dep_sta_tpl["reconcileStatus"] = "applying"
        await camera._process_deploy_status_topic(wrap_dep_sta(dep_sta_tpl))
        assert camera.deploy_stage.value == DeployStage.WaitAppliedConfirmation

        dep_sta_tpl["reconcileStatus"] = "ok"
        await camera._process_deploy_status_topic(wrap_dep_sta(dep_sta_tpl))
        assert camera.deploy_stage.value == DeployStage.Done
        assert camera.deploy_operation.value is None


@pytest.mark.trio
async def test_process_deploy_fsm_evp1_error(nursery, tmp_path) -> None:
    camera = CameraState()

    # setup for parsing deployment status messages
    camera._onwire_schema = OnWireProtocol.EVP1
    wrap_dep_sta = lambda dep_sta: {"deploymentStatus": json.dumps(dep_sta)}

    # Dummy module to deploy
    module = tmp_path / "module"
    module.touch()

    # async setup
    with (
        patch("local_console.core.commands.deploy.SyncWebserver"),
        patch("local_console.core.camera.state.Agent") as mock_agent,
    ):
        camera.set_nursery(nursery)
        mock_agent.onwire_schema = camera._onwire_schema
        mock_agent.deploy = AsyncMock()

        # initial state
        assert camera.deploy_operation.value is None
        assert camera.deploy_stage.value is None

        # trigger deployment
        camera.module_file.value = module
        await camera.do_app_deployment(mock_agent)
        assert camera.deploy_operation.value == DeploymentType.Application
        assert camera.deploy_stage.value == DeployStage.WaitAppliedConfirmation
        dep_sta_tpl = template_deploy_status_for_manifest(camera._deploy_fsm._to_deploy)

        dep_sta_tpl["reconcileStatus"] = "applying"
        await camera._process_deploy_status_topic(wrap_dep_sta(dep_sta_tpl))
        assert camera.deploy_stage.value == DeployStage.WaitAppliedConfirmation

        module_id = next(iter(dep_sta_tpl["modules"].keys()))
        dep_sta_tpl["modules"][module_id]["status"] = "error"
        await camera._process_deploy_status_topic(wrap_dep_sta(dep_sta_tpl))
        assert camera.deploy_stage.value == DeployStage.Error
        assert camera.deploy_operation.value is None
