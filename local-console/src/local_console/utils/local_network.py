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

from local_console.utils._local_network import _get_my_ip_by_routing
from local_console.utils._local_network import _get_network_ifaces
from local_console.utils._local_network import _is_localhost
from local_console.utils._local_network import _is_valid_host
from local_console.utils._local_network import _replace_local_address
from local_console.utils._local_network import LOCAL_IP  # noqa

logger = logging.getLogger(__file__)


def get_network_ifaces() -> list[str]:
    return _get_network_ifaces()


def get_my_ip_by_routing() -> str:
    return _get_my_ip_by_routing()


def is_localhost(hostname: str) -> bool:
    return _is_localhost(hostname)


def replace_local_address(hostname: str) -> str:
    return _replace_local_address(hostname)


def is_valid_host(hostname: str) -> bool:
    return _is_valid_host(hostname)
