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
from local_console.core.camera.enums import StreamStatus
from local_console.gui.controller.base_controller import BaseController
from local_console.gui.driver import Driver
from local_console.gui.model.inference_screen import InferenceScreenModel
from local_console.gui.view.inference_screen.inference_screen import InferenceScreenView


class InferenceScreenController(BaseController):
    """
    The `InferenceScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: InferenceScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = InferenceScreenView(controller=self, model=self.model)

    def refresh(self) -> None:
        assert self.driver.device_manager
        # Trigger for connection status
        proxy = self.driver.device_manager.get_active_device_proxy()
        state = self.driver.device_manager.get_active_device_state()

        if state.stream_status.value is not None:
            self.view.on_stream_status(proxy, state.stream_status.value)

    def unbind(self) -> None:
        self.driver.gui.mdl.unbind(stream_status=self.view.on_stream_status)

    def bind(self) -> None:
        self.driver.gui.mdl.bind(stream_status=self.view.on_stream_status)

    def get_view(self) -> InferenceScreenView:
        return self.view

    def toggle_stream_status(self) -> None:
        assert self.driver.camera_state

        camera_status = self.driver.camera_state.stream_status.value
        if camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)
        else:
            roi = self.driver.camera_state.roi.value
            self.driver.from_sync(self.driver.streaming_rpc_start, roi)

        self.driver.camera_state.stream_status.value = StreamStatus.Transitioning
