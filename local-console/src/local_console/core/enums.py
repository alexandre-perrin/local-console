from enum import Enum
from pathlib import Path

from local_console.utils.enums import StrEnum

DEFAULT_HOME = "~/.config/wedge"


class Config:
    def __init__(self) -> None:
        self.home = DEFAULT_HOME  # type: ignore
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
    def tls_cert_root(self) -> Path:
        return self.home / "tls_client_certs"

    @property
    def cli_cert_pair(self) -> tuple[Path, Path]:
        return self.tls_cert_root / "cli.crt.pem", self.tls_cert_root / "cli.key.pem"

    @property
    def broker_cert_pair(self) -> tuple[Path, Path]:
        return (
            self.tls_cert_root / "broker.crt.pem",
            self.tls_cert_root / "broker.key.pem",
        )

    @property
    def agent_cert_pair(self) -> tuple[Path, Path]:
        return (
            self.tls_cert_root / "agent.crt.pem",
            self.tls_cert_root / "agent.key.pem",
        )

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


class GetObjects(StrEnum):
    INSTANCE = "instance"
    DEPLOYMENT = "deployment"
    TELEMETRY = "telemetry"


class GetCommands(StrEnum):
    GET = "get"
    SET = "set"
    UNSET = "unset"
    SEND = "send"


class EVPEnvVars:
    EVP_IOT_PLATFORM = "EVP_IOT_PLATFORM"
    EVP_MQTT_HOST = "EVP_MQTT_HOST"
    EVP_MQTT_PORT = "EVP_MQTT_PORT"
    EVP_MQTT_CLIENTID = "EVP_MQTT_CLIENTID"
    EVP_DATA_DIR = "EVP_DATA_DIR"
    EVP_HTTPS_CA_CERT = "EVP_HTTPS_CA_CERT"
    EVP_REPORT_STATUS_INTERVAL_MIN_SEC = "EVP_REPORT_STATUS_INTERVAL_MIN_SEC"
    EVP_REPORT_STATUS_INTERVAL_MAX_SEC = "EVP_REPORT_STATUS_INTERVAL_MAX_SEC"
    EVP_MQTT_TLS_CA_CERT = "EVP_MQTT_TLS_CA_CERT"
    EVP_MQTT_TLS_CLIENT_CERT = "EVP_MQTT_TLS_CLIENT_CERT"
    EVP_MQTT_TLS_CLIENT_KEY = "EVP_MQTT_TLS_CLIENT_KEY"


class Target(StrEnum):
    AMD64 = "amd64"
    ARM64 = "arm64"
    XTENSA = "xtensa"


class ModuleExtension(StrEnum):
    WASM = "wasm"
    AOT = "aot"
    SIGNED = "signed"
