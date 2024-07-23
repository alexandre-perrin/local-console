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
import logging
import os
import subprocess
import sys
from base64 import b64decode
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Any
from typing import Optional

logger = logging.getLogger(__file__)


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


def get_output_from_inference_results(raw_data: bytes) -> bytes:
    """
    Extracts output from a device-specific format (`raw_data`):

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

    :param raw_data: binary buffer containing the input data to decode
    :return: base64 decoded value of `Inferences[0]["O"]`.
    """
    data: dict[str, list[dict[str, str]]] = json.loads(raw_data)

    inferences = data["Inferences"]
    if len(inferences) > 1:
        logger.warn("More than 1 inference at a time. Using index 0.")
    output_tensor = inferences[0]["O"]
    return b64decode(output_tensor)


def flatbuffer_binary_to_json(
    fbs: Path,
    inference_data: bytes,
) -> dict[str, Any]:
    """
    Converts a flatbuffers object to a python object via its JSON representation.

    :param fbs: FlatBuffer schema file.
    :inference_data: base64-decoded, flatbuffer-serialized payload to deserialize
    :return: True if success.
    """
    flatc_path = get_flatc()
    try:
        with TemporaryDirectory() as tempdir:
            area = Path(tempdir)

            """
            `flatc` does not support operating over stdin/stdout,
            so a temporary file structure is put in place
            """
            input_file = area / "in" / "payload.bin"
            input_file.parent.mkdir()
            input_file.write_bytes(inference_data)

            output_area = area / "out"
            output_area.mkdir()

            subprocess.run(
                [
                    flatc_path,
                    "--json",
                    "--defaults-json",
                    "--strict-json",
                    "-o",
                    str(output_area),
                    "--raw-binary",
                    str(fbs),
                    "--",
                    str(input_file),
                ],
                check=True,
                text=True,
            )
            generated_files = list(output_area.glob("*"))
            if len(generated_files) != 1:
                raise FlatbufferError(
                    f"Output from flatc did not generate a single file: {str(generated_files)}"
                )
            else:
                decoded: dict[str, Any] = json.load(generated_files[0].open())
                return decoded

    except Exception as e:
        raise FlatbufferError(f"Unexpected error decoding flatbuffers: {e}")


def conform_flatbuffer_schema(fbs: Path) -> bool:
    """
    Verifies if JSON is valid.
    """
    try:
        flatc_path = get_flatc()
        subprocess.check_output(
            [flatc_path, "--conform", fbs], stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        raise FlatbufferError(e.output)

    return True


def get_flatc() -> str:
    """
    For linux, this has no relevant effects.
    For windows, the installer script placed the flatc binary
                 within the virtualenv's scripts directory.
    """
    env_root = str(Path(sys.executable).parent)
    current_path = os.environ.get("PATH", "")
    if env_root not in current_path.split(os.pathsep):
        os.environ["PATH"] = current_path + os.pathsep + env_root

    # Resolve the path to flatc from the PATH
    flatc_path = which("flatc")
    if not flatc_path:
        raise FlatbufferError("flatc not found in PATH")
    else:
        return flatc_path
