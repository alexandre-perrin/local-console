import logging
import os
import subprocess
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from wedge_cli.core.config import get_deployment_schema
from wedge_cli.utils.enums import Commands
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import ModuleExtension
from wedge_cli.utils.enums import Target
from wedge_cli.utils.signature import sign

COMPILATION_FLAGS = {
    Target.AMD64: "--target=x86_64 --cpu=skylake --disable-simd --size-level=1",
    Target.ARM64: "--target=aarch64",
    Target.XTENSA: "--target=xtensa --enable-multi-thread",
}

logger = logging.getLogger(__name__)

app = typer.Typer(help="Command for compiling the modules of the application")


def compile_wasm(flags: Optional[list[str]]) -> None:
    env = os.environ.copy()
    wasi_sdk_root = get_clang_root(env)
    env["WASI_SDK_PATH"] = str(wasi_sdk_root)
    try:
        subprocess.run([Commands.MAKE, Commands.CLEAN])
        cmd = [Commands.MAKE.value]
        if flags:
            cmd += flags
        # TODO: check process return code
        subprocess.run(cmd, env=env)  # type: ignore
    except FileNotFoundError:
        logger.error("Error when running")
        exit(1)


def sign_file(file: str, secret_path: Path) -> None:
    if not secret_path.exists():
        logger.error("Secret does not exist")
        exit(1)

    logger.info(f"Signing {file}")
    with open(f"bin/{file}", "rb") as f:
        aot_bytes = f.read()
    with open(secret_path, "rb") as f:
        secret_bytes = f.read()
    try:
        signed_aot_bytes = sign(aot_bytes, secret_bytes)
    except Exception as e:
        logger.error(f"Error while signing the module {file}: {str(e)}")
        exit(1)

    file = f"{file}.{ModuleExtension.SIGNED}"
    with open(f"bin/{file}", "wb") as f:
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
            exit(1)
    except FileNotFoundError:
        logger.error("wamrc not in PATH")
        exit(1)
    return file


@app.callback(invoke_without_command=True)
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
            exit(1)
        if target:
            file = compile_aot(module_name, target)
        if secret:
            sign_file(file, secret)
