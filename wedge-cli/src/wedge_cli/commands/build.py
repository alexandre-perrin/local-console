import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path

from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import Target


logger = logging.getLogger(__name__)


COMPILATION_FLAGS = {
    Target.AMD64: "--target=x86_64 --cpu=skylake --disable-simd --size-level=1",
    Target.ARM64: "--target=aarch64",
}


def _calculate_sha256(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        sha256_hash.update(f.read())
    return sha256_hash.hexdigest()


def build(**kwargs: dict) -> None:
    config = get_config()
    try:
        # TODO: check process return code
        subprocess.run(["make", "clean"])
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
                subprocess.run(["wamrc", *options.split(" ")])
            except FileNotFoundError:
                logger.error("wamrc not in PATH")
                exit(1)

        deployment["deployment"]["modules"][module]["hash"] = _calculate_sha256(
            str(Path("bin") / file)
        )
        deployment["deployment"]["modules"][module][
            "downloadUrl"
        ] = f"http://{config['webserver']['host']}:8000/bin/{file}"

    with open("deployment.json", "w") as f:
        json.dump(deployment, f, indent=2)
