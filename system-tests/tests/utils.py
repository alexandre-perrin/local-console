import dataclasses
import re
import tarfile
from collections.abc import Generator
from contextlib import suppress
from dataclasses import dataclass

import docker
import pytest

from src.interface import OnWireSchema
from src.interface import OnwireVersion


class InvalidInput(Exception):
    pass


@dataclass
class Options:
    onwire_version: str

    frp_token: str
    frp_host: str
    frp_port: int

    devispare_firmware: str
    devispare_host: str
    devispare_token: str

    local: bool

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

        if not self.local:
            if not self.frp_token:
                raise InvalidInput("FRP Token is a required value")

            if not self.frp_host:
                raise InvalidInput("FRP Host is a required value")

            if not self.frp_port:
                raise InvalidInput("FRP Port is a required value")

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
