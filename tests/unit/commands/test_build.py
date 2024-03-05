import subprocess
from pathlib import Path
from typing import Optional
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import typer
from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.build import app
from wedge_cli.commands.build import COMPILATION_FLAGS
from wedge_cli.commands.build import compile_aot
from wedge_cli.commands.build import compile_wasm
from wedge_cli.commands.build import sign_file
from wedge_cli.core.enums import Commands
from wedge_cli.core.enums import ModuleExtension
from wedge_cli.core.enums import Target
from wedge_cli.core.schemas import DeploymentManifest

from tests.strategies.deployment import deployment_manifest_strategy
from tests.strategies.path import path_strategy

runner = CliRunner()


@given(
    deployment_manifest_strategy(),
    st.lists(st.text(min_size=1, max_size=5), min_size=1, max_size=5),
)
def test_build_command_wasm(
    deployment_manifest: DeploymentManifest, flags: Optional[list[str]]
) -> None:
    wasm_files = []
    for module_file in deployment_manifest.deployment.modules.keys():
        wasm_files.append(f"{module_file}.{ModuleExtension.WASM}")
    with (
        patch("wedge_cli.commands.build.compile_wasm") as mock_compile_wasm,
        patch(
            "wedge_cli.commands.build.os.listdir", return_value=wasm_files
        ) as mock_os_listdir,
        patch(
            "wedge_cli.commands.build.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        command = []
        for flag in flags:
            command.append("-f")
            command.append(flag)
        result = runner.invoke(app, command)
        mock_compile_wasm.assert_called_once_with(flags)
        mock_os_listdir.assert_called_once_with("bin")
        mock_get_deployment.assert_called_once()
        assert result.exit_code == 0


@given(
    deployment_manifest_strategy(),
    st.lists(st.text(min_size=1, max_size=5), min_size=1, max_size=5),
    st.sampled_from(Target),
)
def test_build_command_target(
    deployment_manifest: DeploymentManifest, flags: Optional[list[str]], target: Target
) -> None:
    wasm_files = []
    for module_file in deployment_manifest.deployment.modules.keys():
        wasm_files.append(f"{module_file}.{ModuleExtension.WASM}")
    with (
        patch("wedge_cli.commands.build.compile_wasm") as mock_compile_wasm,
        patch("wedge_cli.commands.build.compile_aot") as mock_compile_aot,
        patch(
            "wedge_cli.commands.build.os.listdir", return_value=wasm_files
        ) as mock_os_listdir,
        patch(
            "wedge_cli.commands.build.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        command = []
        for flag in flags:
            command.append("-f")
            command.append(flag)
        command.append(target.value)
        result = runner.invoke(app, command)
        mock_compile_wasm.assert_called_once_with(flags)
        mock_os_listdir.assert_called_once_with("bin")
        mock_get_deployment.assert_called_once()
        for module_name in deployment_manifest.deployment.modules.keys():
            mock_compile_aot.assert_any_call(module_name, target)
        assert result.exit_code == 0


@given(
    deployment_manifest_strategy(),
    st.text(
        min_size=1,
        max_size=5,
        alphabet=st.characters(
            blacklist_characters="/\0",  # Avoid / and null character
            whitelist_categories=(
                "Lu",
                "Ll",
                "Nd",
                "Pc",
                "Zs",
            ),  # Unicode categories for letters, digits, punctuation, and spaces
        ),
    ),
)
def test_build_command_secret(
    deployment_manifest: DeploymentManifest, secret: str
) -> None:
    wasm_files = []
    for module_file in deployment_manifest.deployment.modules.keys():
        wasm_files.append(f"{module_file}.{ModuleExtension.WASM}")
    with (
        patch("wedge_cli.commands.build.compile_wasm") as mock_compile_wasm,
        patch("wedge_cli.commands.build.sign_file") as mock_sign_file,
        patch(
            "wedge_cli.commands.build.os.listdir", return_value=wasm_files
        ) as mock_os_listdir,
        patch(
            "wedge_cli.commands.build.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        command = ["-s", secret]
        result = runner.invoke(app, command)
        mock_compile_wasm.assert_called_once_with([])
        mock_os_listdir.assert_called_once_with("bin")
        mock_get_deployment.assert_called_once()
        for file in wasm_files:
            mock_sign_file.assert_any_call(file, Path(secret))
        assert result.exit_code == 0


@given(
    deployment_manifest_strategy(),
    st.lists(st.text(min_size=1, max_size=5), max_size=5),
)
def test_build_command_wasm_not_found(
    deployment_manifest: DeploymentManifest, flags: Optional[list[str]]
) -> None:
    with (
        patch("wedge_cli.commands.build.compile_wasm") as mock_compile_wasm,
        patch(
            "wedge_cli.commands.build.os.listdir", return_value=["whatever"]
        ) as mock_os_listdir,
        patch(
            "wedge_cli.commands.build.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        flags_command = []
        for flag in flags:
            flags_command.append("-f")
            flags_command.append(flag)
        result = runner.invoke(app, flags_command)
        mock_compile_wasm.assert_called_once_with(flags)
        mock_os_listdir.assert_called_once_with("bin")
        mock_get_deployment.assert_called_once()
        assert result.exit_code == 1


@given(st.lists(st.text(max_size=5), max_size=5))
def test_compile_wasm(flags: Optional[list[str]]):
    with (
        patch("wedge_cli.commands.build.subprocess.run") as mock_run_agent,
        patch("os.environ.copy", return_value={}) as mock_environ,
        patch(
            "wedge_cli.commands.build.get_clang_root",
            return_value=Path("/opt/wasi-sdk"),
        ) as mock_clang,
    ):
        compile_wasm(flags)
        mock_run_agent.assert_any_call(["make", "clean"])

        cmd = ["make"]
        if flags:
            cmd += flags

        env = {"WASI_SDK_PATH": str(Path("/opt/wasi-sdk"))}
        mock_run_agent.assert_called_with(cmd, env=env)
        mock_clang.assert_called_once()
        mock_environ.assert_called_once()


def test_compile_wasm_file_not_found(flags=[]):
    with (
        patch(
            "wedge_cli.commands.build.subprocess.run", side_effect=FileNotFoundError
        ) as mock_run_agent,
        patch(
            "wedge_cli.commands.build.get_clang_root",
            return_value=Path("/opt/wasi-sdk"),
        ) as mock_clang,
    ):
        with pytest.raises(typer.Exit):
            compile_wasm(flags)
        mock_run_agent.assert_called_once_with(["make", "clean"])
        mock_clang.assert_called_once()


@given(st.text(min_size=1, max_size=5), path_strategy(), st.binary())
def test_sign_file(module_name: str, secret_path: Path, bytes_mock: bytes):
    with (
        patch("wedge_cli.commands.build.Path.exists", return_value=True) as mock_exists,
        patch("builtins.open") as mock_open,
        patch("wedge_cli.commands.build.sign") as mock_sign,
    ):
        file = f"{module_name}.{ModuleExtension.WASM}"
        mock_open.return_value.__enter__.return_value.read.return_value = bytes_mock
        sign_file(file, secret_path)
        mock_exists.assert_called_once()
        mock_open.assert_any_call(secret_path, "rb")
        mock_open.assert_any_call(f"bin/{file}", "rb")
        mock_open.assert_any_call(f"bin/{file}.{ModuleExtension.SIGNED}", "wb")
        mock_sign.assert_called_once_with(bytes_mock, bytes_mock)


@given(st.text(min_size=1, max_size=5), path_strategy())
def test_sign_file_exception(module_name: str, secret_path: Path):
    with (
        patch("wedge_cli.commands.build.Path.exists", return_value=True) as mock_exists,
        patch("builtins.open") as mock_open,
        patch("wedge_cli.commands.build.sign", side_effect=Exception),
    ):
        file = f"{module_name}.{ModuleExtension.WASM}"
        mock_open.return_value.__enter__.return_value.read.return_value = bytes
        with pytest.raises(typer.Exit):
            sign_file(file, secret_path)
        mock_exists.assert_called_once()
        mock_open.assert_any_call(secret_path, "rb")
        mock_open.assert_any_call(f"bin/{file}", "rb")


@given(st.text(min_size=1, max_size=5), st.sampled_from(Target))
def test_compile_aot(module_name: str, target: Target):
    result = Mock()
    result.returncode = 0
    options = COMPILATION_FLAGS[target]
    file = f"{module_name}.{target}.{ModuleExtension.AOT}"
    options += f" -o bin/{file} bin/{module_name}.{ModuleExtension.WASM}"
    with patch(
        "wedge_cli.commands.build.subprocess.run", return_value=result
    ) as mock_wamrc:
        compile_aot(module_name, target)
        mock_wamrc.assert_called_with(
            [Commands.WAMRC.value, *options.split(" ")],
            stdout=subprocess.PIPE,
            text=True,
        )


@given(st.text(min_size=1, max_size=5), st.sampled_from(Target))
def test_compile_aot_wamrc_fail(module_name: str, target: Target):
    result = Mock()
    result.returncode = 1
    options = COMPILATION_FLAGS[target]
    file = f"{module_name}.{target}.{ModuleExtension.AOT}"
    options += f" -o bin/{file} bin/{module_name}.{ModuleExtension.WASM}"
    with patch(
        "wedge_cli.commands.build.subprocess.run", return_value=result
    ) as mock_wamrc:
        with pytest.raises(typer.Exit):
            compile_aot(module_name, target)
        mock_wamrc.assert_called_with(
            [Commands.WAMRC.value, *options.split(" ")],
            stdout=subprocess.PIPE,
            text=True,
        )


@given(st.text(min_size=1, max_size=5), st.sampled_from(Target))
def test_compile_aot_file_not_found(module_name: str, target: Target):
    with patch(
        "wedge_cli.commands.build.subprocess.run", side_effect=FileNotFoundError
    ):
        with pytest.raises(typer.Exit):
            compile_aot(module_name, target)
