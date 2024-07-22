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
from unittest.mock import patch

import pytest
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import map_class_id_to_name


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


def test_map_class_id_to_name(tmp_path) -> None:
    label_file = tmp_path / "label.txt"
    label_file.write_text("Apple\nBanana")

    class_id_to_name = map_class_id_to_name(label_file)
    assert class_id_to_name == {0: "Apple", 1: "Banana"}


def test_map_class_id_to_name_file_not_found(tmp_path) -> None:
    label_file = tmp_path / "non-existent.txt"
    assert not label_file.exists()
    with (
        pytest.raises(FlatbufferError, match="Error while reading labels text file."),
    ):
        map_class_id_to_name(label_file)


def test_map_class_id_to_name_exception(tmp_path) -> None:
    label_file = tmp_path / "label.txt"
    label_file.write_text("Apple\nBanana")

    with (
        patch("pathlib.Path.open", side_effect=Exception),
        pytest.raises(
            FlatbufferError, match="Unknown error while reading labels text file"
        ),
    ):
        map_class_id_to_name(label_file)


def test_map_class_id_to_name_none(tmp_path) -> None:
    class_id_to_name = map_class_id_to_name(None)
    assert class_id_to_name is None
