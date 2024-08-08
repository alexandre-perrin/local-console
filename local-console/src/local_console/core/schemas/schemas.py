# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import json
import logging
from typing import Annotated
from typing import Optional

from local_console.utils.enums import StrEnum
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


IPAddress = Field(pattern=r"^[\w\d_][\w.-]*$")

IPPortNumber = Field(ge=0, le=65535)


class Libraries(BaseModel):
    libraries: list[Optional[str]]


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

    def render_for_evp1(self) -> str:
        # The actual manifest, which is the value of the "deployment" key, is stringified. See:
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/manifest.c#L1151
        # Also, the fields differ and EVP1 has two mandatory fields in the instanceSpecs:
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/manifest.c#L842
        body = self.deployment
        difference_hack = body.model_dump()
        for instance in difference_hack["instanceSpecs"].values():
            instance.update({"version": 1, "entryPoint": "main"})
        as_json = json.dumps(difference_hack)
        return json.dumps({"deployment": as_json})

    def render_for_evp2(self) -> str:
        # A direct JSON serialization, see:
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/manifest.c#L1168
        return json.dumps(self.model_dump())


class DesiredDeviceConfig(BaseModel):
    reportStatusIntervalMax: Annotated[int, Field(ge=0, le=65535)]
    reportStatusIntervalMin: Annotated[int, Field(ge=0, le=65535)]


class OnWireProtocol(StrEnum):
    # Values coming from
    # https://github.com/midokura/evp-onwire-schema/blob/26441528ca76895e1c7e9569ba73092db71c5bc1/schema/systeminfo.schema.json#L42
    # https://github.com/midokura/evp-onwire-schema/blob/1164987a620f34e142869f3979ca63b186c0a061/schema/systeminfo/systeminfo.schema.json#L19
    EVP1 = "EVP1"
    EVP2 = "EVP2-TB"
    # EVP2 on C8Y not implemented at this time

    def for_agent_environ(self) -> str:
        if self == self.EVP1:
            return "evp1"

        return "tb"

    @classmethod
    def from_iot_spec(cls, value: str) -> "OnWireProtocol":
        if value.lower() == "tb":
            return cls.EVP2
        elif value.lower() == "evp1":
            return cls.EVP1
        raise ValueError(f"On-wire schema version unavailable for spec '{value}'")


class DeviceListItem(BaseModel):
    name: str
    port: Annotated[int, IPPortNumber]


class MQTTParams(BaseModel, validate_assignment=True):
    host: str = IPAddress
    port: int = IPPortNumber
    device_id: Optional[Annotated[str, Field(pattern=r"^[_a-zA-Z][\w_.-]*$")]]


class WebserverParams(BaseModel):
    host: str = IPAddress
    port: int = IPPortNumber


DeviceName = Field(pattern=r"^[A-Za-z0-9\-_.]+$", min_length=1, max_length=15)


class Persist(BaseModel):
    module_file: str | None = None
    ai_model_file: str | None = None
    image_dir_path: str | None = None
    inference_dir_path: str | None = None
    size: str | None = None
    unit: str | None = None
    vapp_type: str | None = None
    vapp_schema_file: str | None = None
    vapp_config_file: str | None = None
    vapp_labels_file: str | None = None


class DeviceConnection(BaseModel):
    mqtt: MQTTParams
    webserver: WebserverParams
    name: str = DeviceName
    persist: Persist = Persist()


class EVPParams(BaseModel):
    iot_platform: str = Field(pattern=r"^[a-zA-Z][\w]*$")


class GlobalConfiguration(BaseModel):
    evp: EVPParams
    devices: list[DeviceConnection]
    active_device: int = IPPortNumber
