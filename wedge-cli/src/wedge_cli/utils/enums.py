from enum import Enum
from pathlib import Path


class Config:
    def __init__(self) -> None:
        self.home = Path.home()
        self.wedge = Path(".config_paths/wedge")
        self._config_file = "config_paths.ini"
        self._https_ca_file = "mozilla-root-ca.pem"
        self._https_ca_url = "https://ccadb-public.secure.force.com/mozilla/IncludedRootsPEMTxt?TrustBitsInclude=Websites"
        self._evp_data = "evp_data"

    @property
    def config_path(self) -> Path:
        return self.home / self.wedge / self._config_file

    @property
    def https_ca_path(self) -> Path:
        return self.home / self.wedge / self._https_ca_file

    @property
    def https_ca_url(self) -> str:
        return self._https_ca_url

    @property
    def evp_data_path(self) -> Path:
        return self.home / self.wedge / self._evp_data

    @property
    def wedge(self) -> Path:
        return self._wedge

    @wedge.setter
    def wedge(self, value: str) -> None:
        self._wedge = Path(value)


config_paths = Config()


class Command(str, Enum):
    START = "start"
    DEPLOY = "deploy"
    GET = "get"
    CONFIG = "config"
    LOGS = "logs"
    BUILD = "build"
    NEW = "new"
    RPC = "rpc"


class GetObjects(str, Enum):
    INSTANCE = "instance"
    DEPLOYMENT = "deployment"
    TELEMETRY = "telemetry"


class Target(Enum):
    AMD64 = "amd64"
    ARM64 = "arm64"

    def __str__(self) -> str:
        return self.value
