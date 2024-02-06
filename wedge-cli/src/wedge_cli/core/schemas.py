import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator
from pydantic import ValidationInfo
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class IPAddress(BaseModel):
    ip_value: str = Field(pattern=r"^[\w.-]+$")

    @model_serializer
    def ser_model(self) -> str:
        return self.ip_value

    def __str__(self) -> str:
        return self.ip_value


IPPortNumber = Field(ge=0, le=65535)


class RemoteConnectionInfo(BaseModel):
    host: Optional[IPAddress]
    port: Optional[Annotated[int, IPPortNumber]]

    @property
    def is_enabled(self) -> bool:
        return not (self.host is None or self.port is None)


class TLSConfiguration(BaseModel):
    ca_certificate: Optional[Path]
    ca_key: Optional[Path]

    @field_validator("*")
    @classmethod
    def optional_path_with_expanduser(
        cls, value: Optional[Path], info: ValidationInfo
    ) -> Optional[Path]:
        if not value:
            return None
        else:
            return value.expanduser()

    @property
    def is_valid(self) -> bool:
        return isinstance(self.ca_certificate, Path) and isinstance(self.ca_key, Path)

    @model_validator(mode="after")
    def check_files_are_ok(self) -> "TLSConfiguration":
        if self.is_valid:
            for path, field in zip(
                (self.ca_certificate, self.ca_key), ("ca_certificate", "ca_key")
            ):
                assert path  # make mypy happy
                if not path.is_file():
                    raise PydanticCustomError(
                        "file_not_exists",
                        "Specified path {path} for field '{field}' does not exist.",
                        {"path": path, "field": field},
                    )
        return self


class Libraries(BaseModel):
    libraries: list[Optional[str]]


class EVPParams(BaseModel):
    iot_platform: str = Field(pattern=r"^[a-zA-Z][\w]*$")


class MQTTParams(BaseModel, validate_assignment=True):
    host: IPAddress
    port: int = IPPortNumber
    device_id: Optional[Annotated[str, Field(pattern=r"^[_a-zA-Z][\w_.-]*$")]]


class WebserverParams(BaseModel):
    host: IPAddress
    port: int = IPPortNumber


class AgentConfiguration(BaseModel):
    evp: EVPParams
    mqtt: MQTTParams
    webserver: WebserverParams
    tls: TLSConfiguration

    @property
    def is_tls_enabled(self) -> bool:
        return self.tls.is_valid


class InstanceSpec(BaseModel):
    moduleId: str
    subscribe: dict[str, str] = {}
    publish: dict[str, str] = {}


class Module(BaseModel):
    entryPoint: str
    moduleImpl: str
    downloadUrl: str
    hash: str


class Topics(BaseModel):
    type: str
    topic: str


class Deployment(BaseModel):
    deploymentId: str
    instanceSpecs: dict[str, InstanceSpec]
    modules: dict[str, Module]
    publishTopics: dict[str, Topics]
    subscribeTopics: dict[str, Topics]


class DeploymentManifest(BaseModel):
    deployment: Deployment
