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
from typing import Any

import cv2  # type: ignore
from local_console.core.schemas.tasks.classification import Classification
from local_console.gui.drawer.drawer import Drawer

# Maximum classes to draw
TOPK = 5


class ClassificationDrawer(Drawer):
    @staticmethod
    def process_frame(image: Path, output_tensor: Any) -> None:
        if not isinstance(output_tensor, dict):
            return

        img = cv2.imread(image)

        obj = Classification(**output_tensor)

        img_height = img.shape[0]
        base_font_scale = 0.4
        font_scale = base_font_scale * (img_height / 300.0)
        font_thickness = int(font_scale * 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_color = (255, 255, 255)
        line_type = cv2.LINE_AA

        initial_x = 10
        initial_y = 10
        padding = int(10 * font_scale)

        for cls in obj.perception.classification_list[:TOPK]:
            text = (
                f"{cls.class_name if cls.class_name else cls.class_id}: {cls.score:.2f}"
            )
            (w, h), b = cv2.getTextSize(text, font, font_scale, font_thickness)

            bot_left = (initial_x, initial_y + h + b)

            top_left = (initial_x, initial_y)
            bot_right = (initial_x + w, initial_y + h + b + padding)

            cv2.rectangle(img, top_left, bot_right, (0, 0, 0), cv2.FILLED)

            cv2.putText(
                img,
                text,
                bot_left,
                font,
                font_scale,
                font_color,
                font_thickness,
                line_type,
            )

            initial_y += b + h + padding

        cv2.imwrite(image, img)
