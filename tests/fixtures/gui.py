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
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.config import config_to_schema
from local_console.core.config import get_default_config
from local_console.core.config import setup_default_config
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.gui.model.camera_proxy import CameraStateProxy


def get_default_config_as_schema() -> AgentConfiguration:
    return config_to_schema(get_default_config())


@contextmanager
def driver_context():
    """
    Enables testing the Driver business logic with the GUI
    objects mocked, leveraging the CameraStateProxy interface.
    """
    with (
        patch("local_console.gui.utils.sync_async.run_on_ui_thread", lambda fn: fn),
        patch("local_console.gui.utils.sync_async.SyncAsyncBridge"),
        patch("local_console.gui.driver.get_config", get_default_config_as_schema),
        patch("local_console.gui.driver.Driver.from_sync"),
    ):
        from local_console.gui.driver import Driver

        mock_gui = Mock()
        mock_gui.mdl = CameraStateProxy()
        driver = Driver(mock_gui)
        yield driver, mock_gui


@pytest.fixture()
def driver_set():
    """
    Enables testing the Driver business logic with the GUI
    objects mocked, leveraging the CameraStateProxy interface.
    """
    # Generate default config file if missing
    setup_default_config()
    with driver_context() as (driver, mock_gui):
        yield driver, mock_gui
