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
from unittest.mock import patch

import pytest
from local_console.core.config import Config
from local_console.core.config import config_obj


@pytest.fixture(autouse=True)
def reset_global_config():
    """
    Each test restores the default configuration
    """
    config_obj._config = Config.get_default_config()
    yield


@pytest.fixture(autouse=True)
def skip_local_network():
    with (
        patch(
            "local_console.utils.local_network.get_network_ifaces",
            return_value=["enp5s0"],
        ),
        patch(
            "local_console.utils.local_network.get_my_ip_by_routing",
            return_value="localhost",
        ),
        patch("local_console.utils.local_network.is_localhost", return_value=False),
        patch("local_console.utils.local_network.is_valid_host", return_value=False),
    ):
        yield


@pytest.fixture(autouse=True)
def skip_broker():
    with (
        patch(
            "local_console.servers.broker.spawn_broker",
        ),
    ):
        yield
