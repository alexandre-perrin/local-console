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
import allure
from src.lc_adapter import LocalConsoleAdapter

from tests.matchers.is_equal import equal_to


@allure.parent_suite("Module Direct Command")
@allure.suite("Camera Crop Opt")
def test_change_value(mqtt_broker: LocalConsoleAdapter) -> None:
    allure.dynamic.title("Change Value - Onwire: EVP1 - Interface v1")

    mqtt_broker.publish_mdc(
        "backdoor-EA_Main",
        "SetCameraCropOptValue",
        {
            "CropOptValue": 100,
        },
    )

    mqtt_broker.wait_mdc_response(
        equal_to(
            {"Result": "Succeeded"},
        ),
        timeout=30,
    )

    mqtt_broker.publish_mdc("backdoor-EA_Main", "GetCameraCropOptValue", {})

    mqtt_broker.wait_mdc_response(
        equal_to(
            {"Result": "Succeeded", "CropOptValue": 100},
        ),
        timeout=30,
    )
