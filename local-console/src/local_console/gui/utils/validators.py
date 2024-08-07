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

from local_console.core.schemas.schemas import MQTTParams
from local_console.core.schemas.schemas import WebserverParams
from local_console.utils.local_network import is_valid_host
from pydantic import ValidationError
from pydantic.networks import IPvAnyAddress

logger = logging.getLogger(__name__)


def validate_hostname(host: str) -> bool:
    try:
        WebserverParams(host=host, port=1883)
    except ValidationError as e:
        logger.warning(f"Validation error of hostname: {e}")
        return False

    if not is_valid_host(host):
        return False
    return True


def validate_ip_address(ip: str) -> bool:
    try:
        IPvAnyAddress(ip)
    except ValueError as e:
        logger.warning(f"Validation error of IP address: {e}")
        return False
    return True


def validate_port(port: str) -> bool:
    try:
        MQTTParams(
            host="localhost",
            port=int(port),
            device_id=None,
        )
    except ValueError as e:
        logger.warning(f"Validation error of MQTT port: {e}")
        return False
    return True
