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
import base64
import json
from unittest.mock import patch

from local_console.utils.flatbuffers import FlatBuffers

fb = FlatBuffers()


def test_flatbuffer_binary_to_json(tmp_path):
    with patch(
        "local_console.utils.flatbuffers.subprocess.call",
    ) as mock_call:
        assert fb.flatbuffer_binary_to_json(
            tmp_path / "myschema",
            base64.b64decode(
                "AACQvgAAmD4AAJA+AAAAvQAAQD4AAMC+AAAkvwAABD8AALA+AADwvg=="
            ),
            "myresult",
            tmp_path,
        )
        mock_call.assert_called_once_with(
            [
                fb.get_flatc(),
                "--json",
                "--defaults-json",
                "--strict-json",
                "-o",
                str(tmp_path),
                "--raw-binary",
                str(tmp_path / "myschema"),
                "--",
                str(tmp_path / "myresult.txt"),
            ]
        )


def test_get_output_from_inference_results(tmp_path):
    fb_encoded = "AACQvgAAmD4AAJA+AAAAvQAAQD4AAMC+AAAkvwAABD8AALA+AADwvg=="
    path_txt = tmp_path / "mytext"
    with open(path_txt, "w") as f:
        json.dump(
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
            },
            f,
        )
    assert fb.get_output_from_inference_results(path_txt) == base64.b64decode(
        fb_encoded
    )


def test_flatbuffer_binary_to_json_error(tmp_path):
    path_txt = tmp_path / "mytext"
    with open(path_txt, "w") as f:
        json.dump({}, f)

    assert not fb.flatbuffer_binary_to_json(
        tmp_path / "myschema", path_txt, "myresult", tmp_path
    )
