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
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import StreamStatus
from local_console.gui.controller.inference_screen import InferenceScreenController

from tests.fixtures.camera import cs_init
from tests.fixtures.gui import driver_set


@pytest.mark.trio
async def test_toggle_stream_status_active(driver_set, cs_init):
    driver, mock_gui = driver_set
    with (patch("local_console.gui.controller.inference_screen.InferenceScreenView"),):
        controller = InferenceScreenController(Mock(), driver)
        driver.camera_state = cs_init
        driver.camera_state.stream_status.value = StreamStatus.Active
        controller.toggle_stream_status()
        driver.from_sync.assert_called_once_with(driver.streaming_rpc_stop)
        assert driver.camera_state.stream_status.value == StreamStatus.Transitioning


@pytest.mark.trio
async def test_toggle_stream_status_inactive(driver_set, cs_init):
    driver, mock_gui = driver_set
    with (patch("local_console.gui.controller.inference_screen.InferenceScreenView"),):
        controller = InferenceScreenController(Mock(), driver)
        driver.camera_state = cs_init
        driver.camera_state.stream_status.value = StreamStatus.Inactive

        roi = driver.camera_state.roi.value
        controller.toggle_stream_status()
        driver.from_sync.assert_called_once_with(driver.streaming_rpc_start, roi)
        assert driver.camera_state.stream_status.value == StreamStatus.Transitioning


def test_refresh_no_status():
    with (
        patch("local_console.gui.controller.inference_screen.InferenceScreenView"),
        patch(
            "local_console.gui.controller.inference_screen.InferenceScreenView.on_stream_status"
        ) as mock_stream_status,
    ):
        driver = MagicMock()
        mock_state = MagicMock()
        mock_state.stream_status.value = None
        driver.device_manager.get_active_device_state.return_value = mock_state
        inf = InferenceScreenController(MagicMock(), driver)
        inf.refresh()
        mock_stream_status.assert_not_called()


def test_refresh():
    with patch(
        "local_console.gui.controller.inference_screen.InferenceScreenView"
    ) as mock_view:

        driver = MagicMock()
        inf = InferenceScreenController(MagicMock(), driver)
        inf.refresh()
        mock_view().on_stream_status.assert_called_once_with(
            driver.device_manager.get_active_device_proxy(),
            driver.device_manager.get_active_device_state().stream_status.value,
        )
