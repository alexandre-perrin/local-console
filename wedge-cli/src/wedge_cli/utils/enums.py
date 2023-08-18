from enum import Enum
from pathlib import Path


class Config:
    CONFIG_PATH = Path.home() / ".config/wedge/config.ini"
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
