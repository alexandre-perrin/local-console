from enum import Enum
from pathlib import Path


class Config:
    CONFIG_PATH = Path.home() / ".config/wedge/config.ini"
    HTTPS_CA_PATH = Path.home() / ".config/wedge/mozilla-root-ca.pem"
    HTTPS_CA_URL = "https://ccadb-public.secure.force.com/mozilla/IncludedRootsPEMTxt?TrustBitsInclude=Websites"
    EVP_DATA = Path.home() / ".config/wedge/evp_data"


class Command(str, Enum):
    START = "start"
    DEPLOY = "deploy"
    GET = "get"
    CONFIG = "config"
    LOGS = "logs"
    BUILD = "build"
    NEW = "new"


class GetObjects(str, Enum):
    INSTANCE = "instance"
    DEPLOYMENT = "deployment"
    TELEMETRY = "telemetry"


class Target(Enum):
    AMD64 = "amd64"
    ARM64 = "arm64"

    def __str__(self) -> str:
        return self.value
