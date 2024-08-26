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

from local_console.core.camera.enums import StreamStatus
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.gui.view.base_screen import BaseScreenView


class InferenceScreenView(BaseScreenView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def on_stream_status(self, instance: CameraStateProxy, value: StreamStatus) -> None:
        stream_active = value == StreamStatus.Active
        self.ids.stream_flag.text = value.value
        self.ids.btn_stream_control.style = (
            "elevated" if not stream_active else "filled"
        )
