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
from typing import Any

from kivy.properties import BooleanProperty
from local_console.core.camera.axis_mapping import DEFAULT_ROI
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import StreamStatus
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.view.base_screen import BaseScreenView
from local_console.gui.view.common.components import (
    ImageWithROI,
)
from local_console.gui.view.common.components import ROIState


class StreamingScreenView(BaseScreenView):

    can_stream = BooleanProperty(False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ids.stream_image.bind(state=self.on_roi_state)
        self.ids.stream_image.bind(roi=self.on_roi_change)

    def on_roi_change(self, instance: ImageWithROI, value: UnitROI) -> None:
        self.app.mdl.roi = value

    def on_roi_state(self, instance: ImageWithROI, value: ROIState) -> None:
        if value != ROIState.Disabled:
            if value in (ROIState.Enabled, ROIState.Viewing):
                self.ids.btn_roi_control.style = "elevated"
            else:
                self.ids.btn_roi_control.style = "filled"

    def on_stream_status(self, instance: CameraStateProxy, value: StreamStatus) -> None:
        self.ids.stream_flag.text = value.value
        self.ids.btn_stream_control.style = (
            "elevated" if value != StreamStatus.Active else "filled"
        )

    def on_connected(self, instance: CameraStateProxy, value: bool) -> None:
        self.can_stream = value

    def on_is_streaming(self, instance: CameraStateProxy, value: bool) -> None:
        self.ids.btn_stream_text.text = ("Stop" if value else "Start") + " Streaming"

    def control_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state in (ROIState.Enabled, ROIState.Viewing):
            self.ids.stream_image.start_roi_draw()
        elif roi_state in (ROIState.PickingEndPoint, ROIState.PickingStartPoint):
            self.ids.stream_image.cancel_roi_draw()

    def reset_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state != ROIState.Disabled:
            self.ids.stream_image.cancel_roi_draw()
            self.app.mdl.roi = DEFAULT_ROI
