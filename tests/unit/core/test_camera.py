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
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import trio
from hypothesis import given
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.mixin_mqtt import DEPLOY_STATUS_TOPIC
from local_console.core.camera.mixin_mqtt import EA_STATE_TOPIC
from local_console.core.camera.mixin_mqtt import SYSINFO_TOPIC
from local_console.core.camera.qr import get_qr_object
from local_console.core.camera.qr import qr_string
from local_console.core.camera.state import CameraState
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.gui.drawer.classification import ClassificationDrawer
from local_console.gui.enums import ApplicationType
from local_console.utils.tracking import TrackingVariable

from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_invalid_port_number
from tests.strategies.configs import generate_random_characters
from tests.strategies.configs import generate_valid_device_configuration
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number
from tests.unit.core.test_deploy import template_deploy_status_for_manifest
from tests.unit.gui.test_driver import create_new


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
@given(device_config=generate_valid_device_configuration())
async def test_process_state_topic_correct(device_config: DeviceConfiguration) -> None:
    async with trio.open_nursery() as nursery:
        observer = AsyncMock()
        send_channel, _ = trio.open_memory_channel(0)
        camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
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
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_process_state_topic_wrong(caplog, nursery) -> None:
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
    wrong_obj = {"a": "b"}
    backdoor_state = {
        "state/backdoor-EA_Main/placeholder": b64encode(json.dumps(wrong_obj).encode())
    }
    await camera._process_state_topic(backdoor_state)
    assert "Error while validating device configuration" in caplog.text


@pytest.mark.trio
@given(proto_spec=st.sampled_from(OnWireProtocol))
async def test_process_systeminfo(proto_spec: OnWireProtocol) -> None:
    async with trio.open_nursery() as nursery:
        send_channel, _ = trio.open_memory_channel(0)
        camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())

        sysinfo_report = {"systemInfo": {"protocolVersion": str(proto_spec)}}
        await camera._process_sysinfo_topic(sysinfo_report)

        assert camera.attributes_available
        assert camera._onwire_schema == proto_spec
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_process_deploy_status_evp1(nursery) -> None:
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
    camera._onwire_schema = OnWireProtocol.EVP1
    dummy_deployment = {"a": "b"}

    status_report = {"deploymentStatus": json.dumps(dummy_deployment)}
    await camera._process_deploy_status_topic(status_report)

    assert camera.deploy_status.value == dummy_deployment
    assert camera.attributes_available


@pytest.mark.trio
async def test_process_deploy_status_evp2(nursery) -> None:
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
    camera._onwire_schema = OnWireProtocol.EVP2
    dummy_deployment = {"a": "b"}

    status_report = {"deploymentStatus": dummy_deployment}
    await camera._process_deploy_status_topic(status_report)

    assert camera.deploy_status.value == dummy_deployment
    assert camera.attributes_available


@pytest.mark.trio
async def test_process_incoming_telemetry(nursery) -> None:
    with patch("local_console.core.camera.state.datetime") as mock_time:
        mock_now = Mock()
        mock_time.now.return_value = mock_now

        send_channel, _ = trio.open_memory_channel(0)
        camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
        dummy_telemetry = {"a": "b"}
        await camera.process_incoming("v1/devices/me/telemetry", dummy_telemetry)

        assert camera._last_reception == mock_now


@pytest.mark.trio
@pytest.mark.parametrize(
    "topic, function",
    [
        (EA_STATE_TOPIC, "_process_state_topic"),
        (SYSINFO_TOPIC, "_process_sysinfo_topic"),
        (DEPLOY_STATUS_TOPIC, "_process_deploy_status_topic"),
    ],
)
async def test_process_incoming(topic, function, nursery) -> None:
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())
    with (patch.object(camera, function) as mock_proc,):
        payload = {topic: {"a": "b"}}
        await camera.process_incoming(MQTTTopics.ATTRIBUTES.value, payload)
        mock_proc.assert_awaited_once_with(payload)


@pytest.mark.trio
async def test_process_deploy_fsm_evp2_happy(nursery, tmp_path) -> None:
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())

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
    send_channel, _ = trio.open_memory_channel(0)
    camera = CameraState(send_channel, nursery, trio.lowlevel.current_trio_token())

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


@pytest.mark.trio
async def test_storage_paths(tmp_path_factory, nursery):
    tgd = Path(tmp_path_factory.mktemp("images"))
    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    # Set default image dir
    camera_state.image_dir_path.value = tgd

    # Storing an image when image dir has not changed default
    new_image = create_new(tgd)
    saved = camera_state._save_into_input_directory(new_image, tgd)
    assert saved.parent == tgd

    # Change the target image dir
    new_image_dir = Path(tmp_path_factory.mktemp("another_image_dir"))
    camera_state.image_dir_path.value = new_image_dir

    # Storing an image when image dir has been changed
    new_image = create_new(tgd)
    saved = camera_state._save_into_input_directory(new_image, new_image_dir)
    assert saved.parent == new_image_dir


@pytest.mark.trio
async def test_save_into_image_directory(tmp_path, nursery):
    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    root = tmp_path
    tgd = root / "notexists"

    assert not tgd.exists()
    camera_state.image_dir_path.value = tgd
    assert tgd.exists()

    tgd.rmdir()

    assert not tgd.exists()
    camera_state._save_into_input_directory(create_new(root), tgd)
    assert tgd.exists()


@pytest.mark.trio
async def test_save_into_inferences_directory(tmp_path, nursery):
    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    root = tmp_path
    tgd = root / "notexists"

    assert not tgd.exists()
    camera_state.inference_dir_path.value = tgd
    assert tgd.exists()

    tgd.rmdir()

    assert not tgd.exists()
    camera_state._save_into_input_directory(create_new(root), tgd)
    assert tgd.exists()


@pytest.mark.trio
async def test_process_camera_upload_image(tmp_path_factory, nursery):
    root = tmp_path_factory.getbasetemp()
    inferences_dir = tmp_path_factory.mktemp("inferences")
    images_dir = tmp_path_factory.mktemp("images")

    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    camera_state.inference_dir_path.value = inferences_dir
    camera_state.image_dir_path.value = images_dir

    with (
        patch.object(
            camera_state, "_save_into_input_directory"
        ) as mock_save_into_input_directory,
    ):
        file = root / "images/a.jpg"
        camera_state._process_camera_upload(file)
        mock_save_into_input_directory.assert_called()
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_process_camera_upload_inferences_with_schema(tmp_path_factory, nursery):
    root = tmp_path_factory.getbasetemp()
    inferences_dir = tmp_path_factory.mktemp("inferences")
    images_dir = tmp_path_factory.mktemp("images")

    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    camera_state.inference_dir_path.value = inferences_dir
    camera_state.image_dir_path.value = images_dir

    with (
        patch.object(camera_state, "_save_into_input_directory") as mock_save,
        patch.object(
            camera_state, "_get_flatbuffers_inference_data", return_value={"a": 3}
        ) as mock_get_flatbuffers_inference_data,
        patch(
            "local_console.core.camera.state.get_output_from_inference_results"
        ) as mock_get_output_from_inference_results,
        patch("local_console.gui.driver.Path.read_bytes", return_value=b"boo"),
        patch("local_console.gui.driver.Path.read_text", return_value="boo"),
        patch.object(ClassificationDrawer, "process_frame"),
    ):
        camera_state.vapp_type = TrackingVariable(ApplicationType.CLASSIFICATION.value)
        camera_state.vapp_schema_file.value = Path("objectdetection.fbs")
        ClassificationDrawer.process_frame.side_effect = Exception

        image_file_in = root / "images/a.jpg"
        image_file_saved = images_dir / image_file_in.name
        mock_save.return_value = image_file_saved
        camera_state._process_camera_upload(image_file_in)
        mock_save.assert_called_with(image_file_in, images_dir)

        # A pair has not been formed yet
        ClassificationDrawer.process_frame.assert_not_called()

        inference_file_in = root / "inferences/a.txt"
        inference_file_saved = inferences_dir / inference_file_in.name
        mock_save.return_value = inference_file_saved
        camera_state._process_camera_upload(inference_file_in)
        mock_save.assert_called_with(inference_file_in, inferences_dir)

        mock_get_output_from_inference_results.assert_called_once_with(b"boo")
        ClassificationDrawer.process_frame.assert_called_once_with(
            image_file_saved,
            mock_get_flatbuffers_inference_data.return_value,
        )


@pytest.mark.trio
async def test_process_camera_upload_inferences_missing_schema(
    tmp_path_factory, nursery
):
    root = tmp_path_factory.getbasetemp()
    inferences_dir = tmp_path_factory.mktemp("inferences")
    images_dir = tmp_path_factory.mktemp("images")

    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    camera_state.inference_dir_path.value = inferences_dir
    camera_state.image_dir_path.value = images_dir

    with (
        patch.object(camera_state, "_save_into_input_directory") as mock_save,
        patch.object(camera_state, "_get_flatbuffers_inference_data"),
        patch(
            "local_console.core.camera.state.get_output_from_inference_results"
        ) as mock_get_output_from_inference_results,
        patch("local_console.gui.driver.Path.read_bytes", return_value=b"boo"),
        patch("local_console.gui.driver.Path.read_text", return_value="boo"),
        patch.object(ClassificationDrawer, "process_frame"),
        patch.object(Path, "read_text", return_value=""),
    ):
        camera_state.vapp_type = TrackingVariable(ApplicationType.CLASSIFICATION.value)

        inference_file_in = root / "inferences/a.txt"
        inference_file_saved = inferences_dir / inference_file_in.name
        mock_save.return_value = inference_file_saved
        camera_state._process_camera_upload(inference_file_in)
        mock_save.assert_called_with(inference_file_in, inferences_dir)

        # A pair has not been formed yet
        ClassificationDrawer.process_frame.assert_not_called()

        image_file_in = root / "images/a.jpg"
        image_file_saved = images_dir / image_file_in.name
        mock_save.return_value = image_file_saved
        camera_state._process_camera_upload(image_file_in)
        mock_save.assert_called_with(image_file_in, images_dir)

        mock_get_output_from_inference_results.assert_called_once_with(b"boo")
        ClassificationDrawer.process_frame.assert_called_once_with(
            image_file_saved,
            mock_get_output_from_inference_results.return_value,
        )
