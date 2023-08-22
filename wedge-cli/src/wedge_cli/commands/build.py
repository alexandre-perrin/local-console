import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


def _calculate_sha256(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        sha256_hash.update(f.read())
    return sha256_hash.hexdigest()


def build(**kwargs: dict) -> None:
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
        deployment["deployment"]["modules"][module]["hash"] = _calculate_sha256(
            str(Path("bin") / wasm_file)
        )
        deployment["deployment"]["modules"][module][
            "downloadUrl"
        ] = f"http://localhost:8000/bin/{wasm_file}"

    with open("deployment.json", "w") as f:
        json.dump(deployment, f, indent=2)
