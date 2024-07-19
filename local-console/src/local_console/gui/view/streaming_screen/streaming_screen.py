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
from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from local_console.core.camera import StreamStatus
from local_console.core.camera.axis_mapping import DEFAULT_ROI
from local_console.gui.view.base_screen import BaseScreenView
from local_console.gui.view.common.components import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file
from local_console.gui.view.common.components import ROIState


class StreamingScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.refresh_roi_state(self.ids.stream_image.state)
        self.model_is_changed()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ids.stream_image.bind(roi=self.on_roi_change)

    def on_roi_change(self, instance: ImageWithROI, value: UnitROI) -> None:
        self.app.mdl.roi = value

    def control_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state == ROIState.Disabled:
            self.inform_roi_is_disabled()
        elif roi_state in (ROIState.Enabled, ROIState.Viewing):
            self.ids.stream_image.start_roi_draw()
        else:
            self.ids.stream_image.cancel_roi_draw()

    def reset_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state != ROIState.Disabled:
            self.ids.stream_image.cancel_roi_draw()
            self.controller.set_roi(DEFAULT_ROI)

    def refresh_roi_state(self, roi_state: ROIState) -> None:
        if roi_state != ROIState.Disabled:
            if roi_state in (ROIState.Enabled, ROIState.Viewing):
                self.ids.btn_roi_control.style = "elevated"
            else:
                self.ids.btn_roi_control.style = "filled"

    def model_is_changed(self) -> None:
        stream_active = self.model.stream_status == StreamStatus.Active

        self.ids.stream_flag.text = self.model.stream_status.value
        self.ids.btn_stream_control.style = (
            "elevated" if not stream_active else "filled"
        )
