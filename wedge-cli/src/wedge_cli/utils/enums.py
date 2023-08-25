from enum import Enum
from pathlib import Path


class Config:
    def __init__(self) -> None:
        self.home = "~/.config/wedge"  # type: ignore
        self._config_file = "config.ini"
        self._https_ca_file = "mozilla-root-ca.pem"
        self._https_ca_url = "https://ccadb-public.secure.force.com/mozilla/IncludedRootsPEMTxt?TrustBitsInclude=Websites"
        self._evp_data = "evp_data"

    @property
    def config_path(self) -> Path:
        return self.home / self._config_file

    @property
    def https_ca_path(self) -> Path:
        return self.home / self._https_ca_file

    @property
    def https_ca_url(self) -> str:
        return self._https_ca_url

    @property
    def evp_data_path(self) -> Path:
        return self.home / self._evp_data

    @property
    def home(self) -> Path:
        return self._home

    @home.setter
    def home(self, value: str) -> None:
        self._home = Path(value).expanduser()


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
