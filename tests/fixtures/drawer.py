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

import cv2
import numpy as np
import pytest


@pytest.fixture
def blank_image(tmpdir):
    image_path = Path(tmpdir) / "a.png"
    blank_image_np = np.zeros((10, 10, 3), dtype=np.uint8)
    cv2.imwrite(str(image_path), blank_image_np)
    return image_path, blank_image_np
