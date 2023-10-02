import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path

from wedge_cli.utils.enums import Target
from wedge_cli.utils.signature import sign


logger = logging.getLogger(__name__)


COMPILATION_FLAGS = {
    Target.AMD64: "--target=x86_64 --cpu=skylake --disable-simd --size-level=1",
    Target.ARM64: "--target=aarch64",
    Target.XTENSA: "--target=xtensa --enable-multi-thread",
}


def _calculate_sha256(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        sha256_hash.update(f.read())
    return sha256_hash.hexdigest()


def build(**kwargs: dict) -> None:
    try:
        # TODO: check process return code
        subprocess.run(["make", "clean"])
        if kwargs["flags"]:
            subprocess.run(["make", kwargs["flags"]])  # type: ignore
        else:
            subprocess.run(["make"])
    except FileNotFoundError:
        logger.error("Error when running")
        exit(1)
    try:
        with open("deployment.json") as f:
            deployment = json.load(f)
    except Exception:
        logger.error("deployment.json does not exist")
        exit(1)
    try:
        modules = deployment["deployment"]["modules"].keys()
    except Exception:
        logger.error(
            "deployment.json wrong format. Attribute `deployment.modules` is missing"
        )
        exit(1)
    files = set(os.listdir("bin"))
    for module in modules:
        wasm_file = f"{module}.wasm"
        if wasm_file not in files:
            logger.error(f"{wasm_file} not found")
            exit(1)

        file = wasm_file
        if kwargs["target"]:
            target = kwargs["target"]
            options = COMPILATION_FLAGS[Target(target)]
            file = f"{module}.{target}.aot"
            options += f" -o bin/{file} bin/{module}.wasm"
            try:
                result = subprocess.run(
                    ["wamrc", *options.split(" ")], stdout=subprocess.PIPE, text=True
                )
                if result.returncode != 0:
                    err_msg = result.stdout.rstrip("\n")
                    logger.error(err_msg)
                    exit(1)
            except FileNotFoundError:
                logger.error("wamrc not in PATH")
                exit(1)

        if kwargs["secret"]:
            secret_path = Path(str(kwargs["secret"]))
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

            file = f"{file}.signed"
            with open(f"bin/{file}", "wb") as f:
                f.write(signed_aot_bytes)
