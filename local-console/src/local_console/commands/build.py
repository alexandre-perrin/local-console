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
import logging
import os
import subprocess
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from local_console.core.config import get_deployment_schema
from local_console.core.enums import Commands
from local_console.core.enums import config_paths
from local_console.core.enums import ModuleExtension
from local_console.core.enums import Target
from local_console.utils.signature import sign

COMPILATION_FLAGS = {
    Target.AMD64: "--target=x86_64 --cpu=skylake --disable-simd --size-level=1",
    Target.ARM64: "--target=aarch64",
    Target.XTENSA: "--target=xtensa --enable-multi-thread --size-level=0",
}

logger = logging.getLogger(__name__)

app = typer.Typer()


def compile_wasm(flags: Optional[list[str]]) -> bool:
    success = False

    env = os.environ.copy()
    wasi_sdk_root = get_clang_root(env)
    env["WASI_SDK_PATH"] = str(wasi_sdk_root)
    try:
        subprocess.run([Commands.MAKE, Commands.CLEAN])
        cmd = [Commands.MAKE.value]
        if flags:
            cmd += flags

        proc = subprocess.run(cmd, env=env)  # type: ignore
        success = proc.returncode == 0
    except FileNotFoundError:
        logger.error("Error when running")
        raise typer.Exit(code=1)

    return success


def sign_file(file: str, secret_path: str) -> None:
    if not Path(secret_path).exists():
        logger.error("Secret does not exist")
        raise typer.Exit(code=1)

    logger.info(f"Signing {file}")
    with open(f"{file}", "rb") as f:
        aot_bytes = f.read()
    with open(secret_path, "rb") as f:
        secret_bytes = f.read()
    try:
        signed_aot_bytes = sign(aot_bytes, secret_bytes)
    except Exception as e:
        logger.error(f"Error while signing the module {file}: {str(e)}")
        raise typer.Exit(code=1)

    file = f"{file}.{ModuleExtension.SIGNED}"
    with open(f"{file}", "wb") as f:
        f.write(signed_aot_bytes)


def get_clang_root(env: dict[str, str], compiler_program: str = "clang") -> Path:
    """
    See https://github.com/bytecodealliance/wasm-micro-runtime/blob/main/doc/build_wasm_app.md#aot-compilation-with-3rd-party-toolchains
    """
    wasi_sdk_root = Path(env.get("WASI_SDK_PATH", "/opt/wasi-sdk"))
    clang_bin = wasi_sdk_root / "bin" / compiler_program

    if not clang_bin.is_file():
        raise SystemExit(
            f"Could not find clang (checked for {clang_bin}).\n"
            "If necessary, export the environment variable "
            "WASI_SDK_PATH to the parent of the bin/ directory "
            f"that contains the {compiler_program} executable."
        )
    return wasi_sdk_root


def compile_aot(module_name: str, target: Target) -> str:
    options = COMPILATION_FLAGS[target]
    file = f"{module_name}.{target}.{ModuleExtension.AOT}"
    options += f" -o bin/{file} bin/{module_name}.{ModuleExtension.WASM}"
    try:
        result = subprocess.run(
            [Commands.WAMRC.value, *options.split(" ")],
            stdout=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            err_msg = result.stdout.rstrip("\n")
            logger.error(err_msg)
            raise typer.Exit(code=1)
    except FileNotFoundError:
        logger.error("wamrc not in PATH")
        raise typer.Exit(code=1)
    return file


@app.command(help="Command for compiling the modules of the application")
def build(
    target: Annotated[
        Optional[Target],
        typer.Argument(
            help="Optional argument to specify which AoT compilation to build. If not defined it will only build the plain WASM"
        ),
    ] = None,
    flags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--flag",
            "-f",
            help="Flag to be used in the compilation of the compilations",
        ),
    ] = [],
    secret: Annotated[
        Optional[Path],
        typer.Option("-s", "--secret", help="Path to the ECC key used to sign"),
    ] = None,
) -> None:
    compile_wasm(flags)
    deployment_manifest = get_deployment_schema()
    files = set(os.listdir(config_paths.bin))
    for module_name in deployment_manifest.deployment.modules.keys():
        file = f"{module_name}.{ModuleExtension.WASM}"
        if file not in files:
            logger.error(f"{file} not found")
            raise typer.Exit(code=1)
        if target:
            file = compile_aot(module_name, target)
        if secret:
            sign_file(f"bin/{file}", str(secret))
