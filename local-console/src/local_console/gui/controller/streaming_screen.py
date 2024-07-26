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
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import StreamStatus
from local_console.gui.driver import Driver
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.model.streaming_screen import StreamingScreenModel
from local_console.gui.view.streaming_screen.streaming_screen import StreamingScreenView


class StreamingScreenController:
    """
    The `StreamingScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: StreamingScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = StreamingScreenView(controller=self, model=self.model)

        self.driver.gui.mdl.bind(roi=self.post_roi_actions)

    def get_view(self) -> StreamingScreenView:
        return self.view

    def toggle_stream_status(self) -> None:
        camera_status = self.driver.camera_state.stream_status.value
        if camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)
        else:
            self.driver.from_sync(
                self.driver.streaming_rpc_start, self.driver.camera_state.roi.value
            )
            self.view.ids.stream_image.cancel_roi_draw()

        self.driver.camera_state.stream_status.value = StreamStatus.Transitioning

    def post_roi_actions(self, instance: CameraStateProxy, roi: UnitROI) -> None:
        camera_status = self.driver.camera_state.stream_status.value
        if camera_status == StreamStatus.Transitioning:
            return
        if camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)

        self.driver.camera_state.stream_status.value = StreamStatus.Transitioning
