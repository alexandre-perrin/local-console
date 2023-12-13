import logging
import re
from typing import Optional

from pydantic import BaseModel
from pydantic import field_validator

logger = logging.getLogger(__name__)


class IPAddress(BaseModel):
    ip_value: str

    @field_validator("ip_value")
    def host_port_entry(cls, value: Optional[str]) -> Optional[str]:
        pat = re.compile(r"^[\.\w-]+$")
        if value:
            if not pat.match(value):
                raise ValueError
        return value


class RemoteConnectionInfo(BaseModel):
    host: Optional[IPAddress]
    port: Optional[int]


class Libraries(BaseModel):
    libraries: list[Optional[str]]


class EVPParams(BaseModel):
    iot_platform: str


class MQTTParams(BaseModel):
    host: IPAddress
    port: int
    device_id: Optional[str]


class WebserverParams(BaseModel):
    host: IPAddress
    port: int


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
