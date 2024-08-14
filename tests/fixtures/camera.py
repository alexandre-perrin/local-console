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
from contextlib import asynccontextmanager

import pytest
import trio
from local_console.core.camera.state import CameraState


@pytest.fixture
async def cs_init():
    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(send_channel, trio.lowlevel.current_trio_token())

    yield camera_state


@asynccontextmanager
async def cs_init_context():
    # For using within Hypothesis-driven tests
    send_channel, _ = trio.open_memory_channel(0)
    camera_state = CameraState(send_channel, trio.lowlevel.current_trio_token())

    yield camera_state
