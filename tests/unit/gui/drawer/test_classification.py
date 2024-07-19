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
from pathlib import Path
from unittest.mock import patch

from local_console.gui.drawer.classification import ClassificationDrawer
from tests.fixtures.drawer import blank_image  # noreorder # noqa


def test_process_frame_text(blank_image):
    image_path, _ = blank_image
    output = {
        "perception": {
            "classification_list": [
                {
                    "class_id": 0,
                    "score": 0.1,
                    "class_name": "person",
                }
            ]
        }
    }

    with patch("local_console.gui.drawer.objectdetection.cv2") as mock_cv2:
        ClassificationDrawer.process_frame(image_path, output)
        mock_cv2.putText.call_count == len(output["perception"]["classification_list"])


def test_process_frame_without_output_tensor():
    ClassificationDrawer.process_frame(Path("."), None)
