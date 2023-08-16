from enum import Enum
from pathlib import Path


class Config:
    CONFIG_PATH = Path.home() / ".config/wedge/config.ini"
    EVP_DATA = Path.home() / ".config/wedge/evp_data"


class Subparser(str, Enum):
    START = "start"
