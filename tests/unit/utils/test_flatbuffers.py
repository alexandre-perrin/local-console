import json
import subprocess
from unittest.mock import Mock
from unittest.mock import patch

from hypothesis import given
from wedge_cli.utils.flatbuffers import FlatBuffers

from tests.strategies.configs import generate_text

fb = FlatBuffers()


def test_flatc_conform():
    with patch("wedge_cli.utils.flatbuffers.subprocess") as mock_subprocess:
        path = Mock()
        assert (True, "Success!") == fb.conform_flatbuffer_schema(path)
        mock_subprocess.check_output.assert_called_once_with(
            [fb.get_flatc(), "--conform", path], stderr=mock_subprocess.STDOUT
        )


@given(generate_text())
def test_flatc_conform_called_process_error(output: str):
    with patch(
        "wedge_cli.utils.flatbuffers.subprocess.check_output",
        side_effect=subprocess.CalledProcessError(
            1, Mock(), output=output.encode("utf-8")
        ),
    ):
        path = Mock()
        res_code, res_output = fb.conform_flatbuffer_schema(path)
        assert res_output == output
        assert not res_code


def test_flatc_conform_file_not_found_error():
    with patch(
        "wedge_cli.utils.flatbuffers.subprocess.check_output",
        side_effect=FileNotFoundError,
    ):
        path = Mock()
        res_code, res_output = fb.conform_flatbuffer_schema(path)
        assert res_output == "flatc not in PATH"
        assert not res_code


def test_flatbuffer_binary_to_json(tmp_path):
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
                        "O": "AACQvgAAmD4AAJA+AAAAvQAAQD4AAMC+AAAkvwAABD8AALA+AADwvg==",
                    }
                ],
            },
            f,
        )
    with patch(
        "wedge_cli.utils.flatbuffers.subprocess.call",
    ) as mock_call:
        assert fb.flatbuffer_binary_to_json(
            tmp_path / "myschema", path_txt, "myresult", tmp_path
        )
        mock_call.assert_called_once_with(
            [
                fb.get_flatc(),
                "--json",
                "--defaults-json",
                "--strict-json",
                "-o",
                tmp_path,
                "--raw-binary",
                tmp_path / "myschema",
                "--",
                tmp_path / "myresult.txt",
            ]
        )


def test_flatbuffer_binary_to_json_error(tmp_path):
    path_txt = tmp_path / "mytext"
    with open(path_txt, "w") as f:
        json.dump({}, f)

    assert not fb.flatbuffer_binary_to_json(
        tmp_path / "myschema", path_txt, "myresult", tmp_path
    )
