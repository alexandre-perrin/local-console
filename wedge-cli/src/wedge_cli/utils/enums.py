from enum import Enum
from pathlib import Path


class Config:
    def __init__(self) -> None:
        self.home = "~/.config/wedge"  # type: ignore
        self._config_file = "config.ini"
        self._https_ca_file = "mozilla-root-ca.pem"
        self._https_ca_url = "https://ccadb-public.secure.force.com/mozilla/IncludedRootsPEMTxt?TrustBitsInclude=Websites"
        self._evp_data = "evp_data"
        self.deployment_json = "deployment.json"
        self.bin = "bin"

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


class Commands(str, Enum):
    WAMRC = "wamrc"
    EVP_AGENT = "evp_agent"
    MAKE = "make"
    CLEAN = "clean"


class GetObjects(Enum):
    INSTANCE = "instance"
    DEPLOYMENT = "deployment"
    TELEMETRY = "telemetry"

    def __str__(self) -> str:
        return self.value


class GetCommands(Enum):
    GET = "get"
    SET = "set"
    SEND = "send"

    def __str__(self) -> str:
        return self.value


class EVPEnvVars:
    EVP_IOT_PLATFORM = "EVP_IOT_PLATFORM"
    EVP_MQTT_HOST = "EVP_MQTT_HOST"
    EVP_MQTT_PORT = "EVP_MQTT_PORT"
    EVP_MQTT_CLIENTID = "EVP_MQTT_CLIENTID"
    EVP_DATA_DIR = "EVP_DATA_DIR"
    EVP_HTTPS_CA_CERT = "EVP_HTTPS_CA_CERT"
    EVP_REPORT_STATUS_INTERVAL_MAX_SEC = "EVP_REPORT_STATUS_INTERVAL_MAX_SEC"


class Target(Enum):
    AMD64 = "amd64"
    ARM64 = "arm64"
    XTENSA = "xtensa"

    def __str__(self) -> str:
        return self.value


class ModuleExtension(Enum):
    WASM = "wasm"
    AOT = "aot"
    SIGNED = "signed"

    def __str__(self) -> str:
        return self.value
