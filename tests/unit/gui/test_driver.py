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
import importlib
import random
import shutil
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from local_console.core.camera.axis_mapping import SENSOR_SIZE
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.state import CameraState
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import MQTTParams
from local_console.core.schemas.schemas import WebserverParams

from tests.fixtures.driver import mock_driver_with_agent
from tests.fixtures.driver import mocked_driver_with_agent  # noqa
from tests.mocks.mock_paho_mqtt import MockAsyncIterator
from tests.mocks.mock_paho_mqtt import MockMQTTMessage

# The following lines need to be in this order, in order to
# be able to mock the run_on_ui_thread decorator with
# an identity function
patch(
    "local_console.gui.utils.sync_async.run_on_ui_thread", lambda fn: fn
).start()  # noqa
# TODO: simplify patching
try:
    importlib.reload(sys.modules["local_console.gui.driver"])
except Exception as e:
    print(f"Error while reloading: {e}")
from local_console.gui.driver import Driver  # noqa


def create_new(root: Path) -> Path:
    new_file = root / f"{random.randint(1, int(1e6))}"
    new_file.write_bytes(b"0")
    return new_file


def test_file_move(tmpdir):
    origin = Path(tmpdir.join("fileA"))
    origin.write_bytes(b"0")

    target = Path(tmpdir.mkdir("sub").mkdir("subsub"))
    moved = Path(shutil.move(origin, target))
    assert moved.parent == target


@pytest.mark.trio
@given(st.integers(min_value=0, max_value=65535))
@settings(deadline=1000)
async def test_streaming_stop_required(req_id: int):
    with (mock_driver_with_agent() as (driver, mock_agent),):
        mock_agent.publish = AsyncMock()
        mock_agent.rpc = AsyncMock()
        msg = MockMQTTMessage(f"v1/devices/me/attributes/request/{req_id}", b"{}")
        mock_agent.client.messages.return_value.__aenter__.return_value = (
            MockAsyncIterator([msg])
        )
        async with trio.open_nursery() as nursery:
            send_channel, _ = trio.open_memory_channel(0)
            driver.camera_state = CameraState(
                send_channel, nursery, trio.lowlevel.current_trio_token()
            )
            driver.camera_state.initialize_connection_variables(
                "EVP1",
                DeviceConnection(
                    name="device1",
                    mqtt=MQTTParams(host="localhost", port=1883, device_id="device1"),
                    webserver=WebserverParams(host="localhost", port=8000),
                ),
            )
            with (
                patch.object(
                    driver.camera_state, "streaming_rpc_stop"
                ) as mock_streaming_rpc_stop,
            ):
                await driver.camera_state.mqtt_setup()
                mock_streaming_rpc_stop.assert_awaited_once()
            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_streaming_rpc_start(mocked_driver_with_agent, nursery):
    driver, mock_agent = mocked_driver_with_agent

    mock_agent.publish = AsyncMock()
    mock_rpc = AsyncMock()
    mock_agent.rpc = mock_rpc

    send_channel, _ = trio.open_memory_channel(0)
    driver.camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    driver.camera_state.mqtt_client = mock_agent

    driver.camera_state.image_dir_path.value = Path("my_image_path")
    driver.camera_state.inference_dir_path.value = Path("my_inference_path")
    driver.camera_state.upload_port = 1234
    upload_url = "http://localhost:1234"
    h_size, v_size = SENSOR_SIZE

    await driver.camera_state.streaming_rpc_start()
    mock_rpc.assert_awaited_with(
        "backdoor-EA_Main",
        "StartUploadInferenceData",
        StartUploadInferenceData(
            StorageName=upload_url,
            StorageSubDirectoryPath=str(driver.camera_state.image_dir_path.value),
            StorageNameIR=upload_url,
            StorageSubDirectoryPathIR=str(driver.camera_state.inference_dir_path.value),
            CropHOffset=0,
            CropVOffset=0,
            CropHSize=h_size,
            CropVSize=v_size,
        ).model_dump_json(),
    )


@pytest.mark.trio
async def test_connection_status_timeout(mocked_driver_with_agent, nursery):
    driver, _ = mocked_driver_with_agent
    send_channel, _ = trio.open_memory_channel(0)
    driver.camera_state = CameraState(
        send_channel, nursery, trio.lowlevel.current_trio_token()
    )
    driver.camera_state.stream_status.value = StreamStatus.Active
    await driver.camera_state.connection_status_timeout()
    assert driver.camera_state.stream_status.value == StreamStatus.Inactive


@pytest.mark.trio
async def test_send_ppl_configuration(nursery):
    config = "myconfiguration"
    mock_configure = AsyncMock()
    with (mock_driver_with_agent() as (driver, mock_agent),):
        send_channel, _ = trio.open_memory_channel(0)
        driver.camera_state = CameraState(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )
        driver.camera_state.mqtt_client = mock_agent
        driver.device_manager = MagicMock()

        mock_send_app_config = AsyncMock()
        driver.device_manager.get_active_device_state.return_value = (
            mock_send_app_config
        )

        mock_agent.configure = mock_configure

        await driver.send_app_config(config)
        mock_send_app_config.send_app_config.assert_awaited_with(config)
