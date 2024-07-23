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

import cv2
import numpy as np
from local_console.gui.drawer.objectdetection import DetectionDrawer
from tests.fixtures.drawer import blank_image  # noreorder # noqa


def test_process_frame(blank_image):
    image_path, blank_image_np = blank_image
    left, top, right, bottom = 1, 1, 5, 4
    output = {
        "perception": {
            "object_detection_list": [
                {
                    "class_id": 0,
                    "bounding_box_type": "mytype",
                    "bounding_box": {
                        "top": top,
                        "left": left,
                        "right": right,
                        "bottom": bottom,
                    },
                    "score": 0.1,
                }
            ]
        }
    }

    DetectionDrawer.process_frame(image_path, output)
    expected_image = cv2.rectangle(
        blank_image_np, (left, top), (right, bottom), (0, 0, 255), 2
    )
    expected_image = cv2.putText(
        expected_image,
        "0: 0.1",
        (left, top),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    result_image = cv2.imread(str(image_path))

    assert np.array_equal(result_image, expected_image)


def test_process_frame_text(blank_image):
    image_path, _ = blank_image
    left, top, right, bottom = 1, 1, 5, 4
    output = {
        "perception": {
            "object_detection_list": [
                {
                    "class_id": 0,
                    "bounding_box_type": "mytype",
                    "bounding_box": {
                        "top": top,
                        "left": left,
                        "right": right,
                        "bottom": bottom,
                    },
                    "score": 0.1,
                    "class_name": "person",
                }
            ]
        }
    }

    with patch("local_console.gui.drawer.objectdetection.cv2") as mock_cv2:
        DetectionDrawer.process_frame(image_path, output)
        mock_cv2.putText.assert_called_once_with(
            mock_cv2.rectangle.return_value,
            "person: 0.10",
            (left, top),
            mock_cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )


def test_process_frame_without_output_tensor():
    DetectionDrawer.process_frame(Path("."), None)
