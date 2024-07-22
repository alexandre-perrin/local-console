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
import json
import subprocess
from base64 import b64decode
from io import StringIO
from pathlib import Path
from unittest.mock import ANY
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from hypothesis import given
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.camera.flatbuffers import conform_flatbuffer_schema
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import get_flatc
from local_console.core.camera.flatbuffers import get_output_from_inference_results
from local_console.core.camera.flatbuffers import map_class_id_to_name

from tests.strategies.configs import generate_text


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


def test_get_flatc():
    with (patch("local_console.core.camera.flatbuffers.which", return_value="flatc"),):
        assert get_flatc() == "flatc"


def test_get_flatc_error():
    with (
        patch("local_console.core.camera.flatbuffers.which", return_value=None),
        pytest.raises(FlatbufferError, match="flatc not found in PATH"),
    ):
        get_flatc()


def test_flatc_conform():
    with (
        patch("local_console.core.camera.flatbuffers.subprocess") as mock_subprocess,
        patch("local_console.core.camera.flatbuffers.get_flatc") as mock_flatc,
    ):
        path = Mock()
        assert conform_flatbuffer_schema(path)
        mock_subprocess.check_output.assert_called_once_with(
            [mock_flatc.return_value, "--conform", path],
            stderr=mock_subprocess.STDOUT,
            text=True,
        )


@given(generate_text())
def test_flatc_conform_called_process_error(output: str):
    path = Mock()
    with (
        patch(
            "local_console.core.camera.flatbuffers.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, Mock(), output=output),
        ),
        patch("local_console.core.camera.flatbuffers.get_flatc"),
        pytest.raises(FlatbufferError, match=output),
    ):
        conform_flatbuffer_schema(path)


def test_flatc_conform_file_not_found_error():
    path = Mock()
    with (
        patch(
            "local_console.core.camera.flatbuffers.which",
            return_value=None,
        ),
        pytest.raises(FlatbufferError, match="flatc not found in PATH"),
    ):
        conform_flatbuffer_schema(path)


def test_get_output_from_inference_results(tmp_path):
    fb_encoded = "AACQvgAAmD4AAJA+AAAAvQAAQD4AAMC+AAAkvwAABD8AALA+AADwvg=="
    device_payload = json.dumps(
        {
            "DeviceID": "Aid-00010001-0000-2000-9002-0000000001d1",
            "ModelID": "0300009999990100",
            "Image": True,
            "Inferences": [
                {
                    "T": "20240326110151928",
                    "O": fb_encoded,
                }
            ],
        }
    )
    assert get_output_from_inference_results(device_payload) == b64decode(fb_encoded)


def test_flatbuffer_binary_to_json(tmp_path):
    with (
        patch("local_console.core.camera.flatbuffers.get_flatc") as mock_flatc,
        patch(
            "local_console.core.camera.flatbuffers.subprocess.run",
        ) as mock_run,
        patch(
            "local_console.core.camera.flatbuffers.Path.write_bytes",
        ),
        patch(
            "local_console.core.camera.flatbuffers.Path.glob",
            return_value=[Path()],  # A single file element list
        ),
        patch(
            "local_console.core.camera.flatbuffers.Path.open",
            return_value=StringIO("{}"),  # Mocks an open file handle
        ),
    ):
        assert dict() == flatbuffer_binary_to_json(
            tmp_path / "myschema",
            b"payload",
        )
        mock_run.assert_called_once_with(
            [
                mock_flatc.return_value,
                "--json",
                "--defaults-json",
                "--strict-json",
                "-o",
                ANY,
                "--raw-binary",
                ANY,
                "--",
                ANY,
            ],
            check=True,
            text=True,
        )


def test_flatbuffer_binary_to_json_error(tmp_path):
    path_txt = tmp_path / "mytext"
    path_txt.write_text("{}")
    with pytest.raises(FlatbufferError):
        flatbuffer_binary_to_json(tmp_path / "myschema", b"payload")
