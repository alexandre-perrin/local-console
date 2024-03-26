import base64
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__file__)


class FlatBuffers:
    def conform_flatbuffer_schema(self, fbs: Path) -> tuple[bool, str]:
        """
        Verifies if JSON is valid.
        """
        try:
            subprocess.check_output(
                ["flatc", "--conform", fbs],
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            output = str(e.output, "utf-8")
            return False, output
        except FileNotFoundError:
            output = "flatc not in PATH"
            logger.error("flatc not in PATH")
            return False, output
        return True, "Success!"

    def flatbuffer_binary_to_json(
        self, fbs: Path, output_txt: Path, output_name: str, out_dir: Path
    ) -> bool:
        """
        Converts a device-specific format (`output_txt`):

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

        to JSON format and saves it in `out_dir` as `output_name`.json.

        :param fbs: FlatBuffer schema file.
        :output_txt: Path to the device-specific output tensor.
        :output_name: Base name for the output JSON file.
        :out_dir: Directory where the output JSON file will be saved.
        :return: True if success.
        """
        try:
            with open(output_txt) as f:
                data: dict[str, list[dict[str, str]]] = json.loads(f.read())

            inferences = data["Inferences"]
            if len(inferences) > 1:
                logger.warn("More than 1 inference at a time. Using index 0.")
            output_tensor = inferences[0]["O"]
            output_tensor_decode = base64.b64decode(output_tensor)

            out_path = out_dir / f"{output_name}.txt"
            with open(out_path, "wb") as f:
                f.write(output_tensor_decode)

            subprocess.call(
                [
                    "flatc",
                    "--json",
                    "--strict-json",
                    "-o",
                    out_dir,
                    "--raw-binary",
                    fbs,
                    "--",
                    out_path,
                ]
            )

        except Exception as e:
            logger.error(f"Unexpected format: {e}")
            return False
        return True
