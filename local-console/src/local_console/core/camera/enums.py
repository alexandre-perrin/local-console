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
from enum import Enum

from local_console.utils.enums import StrEnum


class StreamStatus(Enum):
    # Camera states:
    # https://github.com/SonySemiconductorSolutions/EdgeAIPF.smartcamera.type3.mirror/blob/vD7.00.F6/src/edge_agent/edge_agent_config_state_private.h#L309-L314
    Inactive = "Inactive"
    Active = "Active"
    Transitioning = (
        "..."  # Not a CamFW state. Used to describe transition in Local Console.
    )

    @classmethod
    def from_string(cls, value: str) -> "StreamStatus":
        if value in ("Standby", "Error", "PowerOff"):
            return cls.Inactive
        elif value == "Streaming":
            return cls.Active
        return cls.Transitioning


class MQTTTopics(Enum):
    ATTRIBUTES = "v1/devices/me/attributes"
    TELEMETRY = "v1/devices/me/telemetry"
    ATTRIBUTES_REQ = "v1/devices/me/attributes/request/+"
    RPC_RESPONSES = "v1/devices/me/rpc/response/+"


class OTAUpdateStatus(StrEnum):
    DOWNLOADING = "Downloading"
    UPDATING = "Updating"
    REBOOTING = "Rebooting"
    DONE = "Done"
    FAILED = "Failed"


class OTAUpdateModule(StrEnum):
    APFW = "ApFw"
    SENSORFW = "SensorFw"
    DNNMODEL = "DnnModel"


class FirmwareExtension(StrEnum):
    APPLICATION_FW = ".bin"
    SENSOR_FW = ".fpk"


class DeployStage(Enum):
    WaitFirstStatus = "WaitFirstStatus"
    WaitAppliedConfirmation = "WaitAppliedConfirmation"
    Done = "Done"
    Error = "Error"


class DeploymentType(Enum):
    Application = "Application"
