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
from typing import Optional


class FlatbufferError(Exception):
    """
    Used for conveying error messages in a framework-agnostic way
    """


def add_class_names(data: dict, class_id_to_name: dict) -> None:
    # Add class names to the data recursively
    if isinstance(data, dict):
        updates = []
        for key, value in data.items():
            if key == "class_id":
                updates.append(("class_name", class_id_to_name.get(value, "Unknown")))
            else:
                add_class_names(value, class_id_to_name)
        for key, value in updates:
            data[key] = value
    elif isinstance(data, list):
        for item in data:
            add_class_names(item, class_id_to_name)


def map_class_id_to_name(labels_file: Optional[Path]) -> Optional[dict[int, str]]:
    class_id_to_name = None

    if labels_file is not None:
        try:
            class_names = labels_file.read_text().splitlines()
            # Read labels and create a mapping of class IDs to class names
            class_id_to_name = {i: name for i, name in enumerate(class_names)}
        except FileNotFoundError:
            raise FlatbufferError("Error while reading labels text file.")
        except Exception as e:
            raise FlatbufferError(f"Unknown error while reading labels text file: {e}")

    return class_id_to_name
