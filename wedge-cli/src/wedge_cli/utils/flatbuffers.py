import subprocess
from pathlib import Path


class FlatBuffers:
    def conform_flatbuffer_schema(self, fbs: Path) -> tuple[bool, str]:
        try:
            subprocess.check_output(
                ["flatc", "--conform", fbs], stderr=subprocess.STDOUT
            )
            return True, "Success!"
        except subprocess.CalledProcessError as e:
            output = str(e.output, "utf-8")
            return False, output

    def flatbuffer_binary_to_json(self, fbs: Path, bin: Path, out: Path) -> None:
        subprocess.call(
            [
                "flatc",
                "--json",
                "--strict-json",
                "-o",
                out,
                "--raw-binary",
                fbs,
                "--",
                bin,
            ]
        )
