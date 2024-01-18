import logging
from typing import Annotated
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_serializer

logger = logging.getLogger(__name__)


class IPAddress(BaseModel):
    ip_value: str = Field(pattern=r"^[\w.-]+$")

    @model_serializer
    def ser_model(self) -> str:
        return self.ip_value


IPPortNumber = Field(ge=0, le=65535)


class RemoteConnectionInfo(BaseModel):
    host: Optional[IPAddress]
    port: Optional[Annotated[int, IPPortNumber]]


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
