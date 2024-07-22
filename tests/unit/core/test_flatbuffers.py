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
from local_console.core.camera.flatbuffers import add_class_names


def test_add_class_names() -> None:
    class_id_to_name = {
        0: "Apple",
        1: "Banana",
    }
    data = {
        "perception": {
            "classification_list": [
                {
                    "class_id": 0,
                    "score": 0.929688,
                },
                {
                    "class_id": 1,
                    "score": 0.070313,
                },
            ]
        }
    }
    add_class_names(data, class_id_to_name)
    assert data["perception"]["classification_list"][0]["class_name"] == "Apple"
    assert data["perception"]["classification_list"][1]["class_name"] == "Banana"

    class_id_to_name = {
        0: "Apple",
    }
    add_class_names(data, class_id_to_name)
    assert data["perception"]["classification_list"][0]["class_name"] == "Apple"
    assert data["perception"]["classification_list"][1]["class_name"] == "Unknown"
