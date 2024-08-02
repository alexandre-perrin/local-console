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

import pytest
import trio
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.state import CameraState
from local_console.gui.controller.inference_screen import InferenceScreenController

from tests.fixtures.gui import driver_set


@pytest.mark.trio
async def test_toggle_stream_status_active(driver_set, nursery):
    driver, mock_gui = driver_set
    with (patch("local_console.gui.controller.inference_screen.InferenceScreenView"),):
        controller = InferenceScreenController(Mock(), driver)
        send_channel, _ = trio.open_memory_channel(0)
        driver.camera_state = CameraState(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )
        driver.camera_state.stream_status.value = StreamStatus.Active
        controller.toggle_stream_status()
        driver.from_sync.assert_called_once_with(driver.streaming_rpc_stop)
        assert driver.camera_state.stream_status.value == StreamStatus.Transitioning


@pytest.mark.trio
async def test_toggle_stream_status_inactive(driver_set, nursery):
    driver, mock_gui = driver_set
    with (patch("local_console.gui.controller.inference_screen.InferenceScreenView"),):
        controller = InferenceScreenController(Mock(), driver)
        send_channel, _ = trio.open_memory_channel(0)
        driver.camera_state = CameraState(
            send_channel, nursery, trio.lowlevel.current_trio_token()
        )
        driver.camera_state.stream_status.value = StreamStatus.Inactive

        roi = driver.camera_state.roi.value
        controller.toggle_stream_status()
        driver.from_sync.assert_called_once_with(driver.streaming_rpc_start, roi)
        assert driver.camera_state.stream_status.value == StreamStatus.Transitioning
