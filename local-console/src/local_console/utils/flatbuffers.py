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
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__file__)


class FlatBuffers:

    def get_output_from_inference_results(self, output_txt: Path) -> bytes:
        """
        Extracts output from a device-specific format (`output_txt`):

        {
            "DeviceID": "Aid-00010001-0000-2000-9002-0000000001d1",
            "ModelID": "0300009999990100",
            "Image": true,
            "Inferences": [
                {
                    "T": "20240326110151928",
                    "O": "AACQvgAAmD4AAJA+AAAAvQAAQD4AAMC+AAAkvwAABD8AALA+AADwvg=="
                }
            ]
        }

        :param fbs: FlatBuffer schema file.
        :output_txt: Path to the device-specific output tensor.
        :output_name: Base name for the output JSON file.
        :out_dir: Directory where the output JSON file will be saved.
        :return: base64 decoded value of `Inferences[0]["O"]`.
        """
        with open(output_txt) as f:
            data: dict[str, list[dict[str, str]]] = json.loads(f.read())

        inferences = data["Inferences"]
        if len(inferences) > 1:
            logger.warn("More than 1 inference at a time. Using index 0.")
        output_tensor = inferences[0]["O"]
        return base64.b64decode(output_tensor)

    def flatbuffer_binary_to_json(
        self, fbs: Path, output: bytes, output_name: str, out_dir: Path
    ) -> bool:
        """
        Converts a flatbuffers object to JSON format and saves it in `out_dir` as `output_name`.json.

        :param fbs: FlatBuffer schema file.
        :output: Flatbuffers object.
        :output_name: Base name for the output JSON file.
        :out_dir: Directory where the output JSON file will be saved.
        :return: True if success.
        """
        try:
            out_path = out_dir / f"{output_name}.txt"
            with open(out_path, "wb") as f:
                f.write(output)

            flatc_path = self.get_flatc()
            subprocess.call(
                [
                    flatc_path,
                    "--json",
                    "--defaults-json",
                    "--strict-json",
                    "-o",
                    str(out_dir),
                    "--raw-binary",
                    str(fbs),
                    "--",
                    str(out_path),
                ]
            )

        except Exception as e:
            logger.error("Unexpected error decoding flatbuffers:", exc_info=e)
            return False
        return True
