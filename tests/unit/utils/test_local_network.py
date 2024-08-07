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
import logging
import re
from unittest.mock import patch

from hypothesis import given
from local_console.utils._local_network import _get_my_ip_by_routing
from local_console.utils._local_network import _get_network_ifaces
from local_console.utils._local_network import _is_localhost

# For some reason, pycln removes this import, but obviously
# pytest fails when running the tests!
from tests.fixtures.debugging import debug_log  # noreorder # noqa
from tests.strategies.configs import generate_text

logger = logging.getLogger(__name__)


def test_detect_interfaces(debug_log):
    interfaces = _get_network_ifaces()

    assert "lo" not in interfaces
    assert all("docker" not in iface for iface in interfaces)
    assert all("ppp" not in iface for iface in interfaces)


def test_get_my_ip_by_routing():
    # Ensure we get an IPv4 address
    local_ip = _get_my_ip_by_routing()
    assert re.match(r"\d+\.\d+\.\d+\.\d+", local_ip)


def test_is_localhost():
    assert _is_localhost("localhost")
    assert _is_localhost("127.0.0.1")


@given(
    generate_text(),
)
def test_is_localhost_fail(hostname: str):
    assert not _is_localhost("192.168.1.1.1")
    assert not _is_localhost("192.168.1.1")
    assert not _is_localhost(f"{hostname}.")
    assert not _is_localhost("".join(map(str, range(10000))))
    with patch(
        "local_console.utils._local_network.socket.gethostbyname",
        side_effects=Exception,
    ):
        assert not _is_localhost(hostname)
