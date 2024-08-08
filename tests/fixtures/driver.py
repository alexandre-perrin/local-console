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
from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.gui.driver import Driver


@contextmanager
def mock_driver_with_agent():
    agent = MagicMock()
    with (
        patch("local_console.core.camera.mixin_mqtt.TimeoutBehavior"),
        patch("local_console.core.camera.mixin_mqtt.Agent", return_value=agent),
        patch("local_console.core.camera.mixin_mqtt.spawn_broker"),
        patch("local_console.gui.driver.SyncAsyncBridge"),
    ):
        yield (Driver(MagicMock()), agent)


@pytest.fixture()
def mocked_driver_with_agent():
    """
    This construction is necessary because hypothesis does not
    support using custom pytest fixtures from cases that it
    manages (i.e. cases decorated with @given).
    """
    with mock_driver_with_agent() as (driver, agent):
        yield (driver, agent)
