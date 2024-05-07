import dataclasses
import re
import tarfile
from collections.abc import Generator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import docker
import pytest

from src.interface import OnWireSchema
from src.interface import OnwireVersion

BASE_DIR = Path(__file__).parent


class InvalidInput(Exception):
    pass


@dataclass
class Options:
    onwire_version: str

    frp_token: str
    frp_host: str
    frp_port_mqtt: int
    frp_port_http: int
    frp_name_suffix: str

    devispare_firmware: str
    devispare_host: str
    devispare_token: str

    local: bool
    certs_folder: Path

    @classmethod
    def get(cls) -> Generator:
        for field in dataclasses.fields(cls):
            if field.type is bool:
                yield (field.name, {"action": "store_true", "default": False})

            else:
                yield (field.name, {"type": field.type})

    @classmethod
    def load(cls, config: pytest.Config) -> "Options":
        opt = vars(config.option)
        return cls(**{field.name: opt[field.name] for field in dataclasses.fields(cls)})

    def verify(self) -> None:
        onwire_versions = [OnwireVersion.EVP1, OnwireVersion.EVP2]

        if self.onwire_version not in onwire_versions:
            raise InvalidInput(
                f"Onwire Version must be: {' or '.join(onwire_versions)}"
            )

        certs_dir = (
            self.certs_folder
            if self.certs_folder
            else BASE_DIR.parent.joinpath("src/resources/mqtt-broker/certificates")
        )
        if not (
            certs_dir.is_dir()
            and certs_dir.joinpath("ca.crt").is_file()
            and certs_dir.joinpath("ca.key").is_file()
        ):
            raise InvalidInput(f"Invalid certificates path: {certs_dir}")

        if not self.local:
            if not self.frp_token:
                raise InvalidInput("FRP Token is a required value")

            if not self.frp_host:
                raise InvalidInput("FRP Host is a required value")

            if not self.frp_port_mqtt:
                raise InvalidInput("FRP Port for MQTT is a required value")

            if not self.frp_port_http:
                raise InvalidInput("FRP Port for HTTP is a required value")

            if not re.match(r"^http(?:s)?:\/\/.*$", self.devispare_host):
                raise InvalidInput(
                    "DeviSpare host must match regexp: '^http(?:s)?://.*$'"
                )

            if not self._is_firmware_valid():
                raise InvalidInput(
                    "Firmware is not a Tarfile nor a valid Docker Image. "
                    "Review that the File or Image exists. "
                    "Review your Docker credentials or VPN."
                )

            if not self.devispare_token:
                raise InvalidInput("DeviSpare Token is a required value")

    @property
    def onwire_schema(self) -> OnWireSchema:
        return OnWireSchema(self.onwire_version)

    def _is_firmware_valid(self) -> bool:
        dockerc = docker.from_env()

        if dockerc.images.list(name=self.devispare_firmware):
            return True

        with suppress(Exception):
            dockerc.images.pull(self.devispare_firmware)
            return True

        with suppress(Exception):
            return tarfile.is_tarfile(self.devispare_firmware)

        return False
