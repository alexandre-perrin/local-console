import enum
import json
import logging
from base64 import b64decode
from typing import Any

from wedge_cli.clients.agent import Agent

logger = logging.getLogger(__name__)


class Camera:
    """
    This class is a live, read-only interface to most status
    information that the Camera Firmware reports.
    """
    EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
    SYSINFO_TOPIC = "systemInfo"

    def __init__(self) -> None:
        self.sensor_state = StreamStatus.Inactive
        self.app_state = ""
        self.onwire_protocol = OnWireProtocol.UNKNOWN

    @property
    def is_ready(self) -> bool:
        return self.onwire_protocol != OnWireProtocol.UNKNOWN

    def process_incoming(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == Agent.ATTRIBUTES_TOPIC:
            if self.EA_STATE_TOPIC in payload:
                decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
                payload[self.EA_STATE_TOPIC] = decoded

                status = decoded["Status"]
                self.sensor_state = StreamStatus.from_string(status["Sensor"])
                self.app_state = status["ApplicationProcessor"]

            if self.SYSINFO_TOPIC in payload:
                sys_info = payload[self.SYSINFO_TOPIC]
                self.onwire_protocol = OnWireProtocol(sys_info["protocolVersion"])

        logger.critical("Incoming on %s: %s", topic, str(payload))


class OnWireProtocol(enum.Enum):
    # Values coming from
    # https://github.com/midokura/evp-onwire-schema/blob/26441528ca76895e1c7e9569ba73092db71c5bc1/schema/systeminfo.schema.json#L42
    # https://github.com/midokura/evp-onwire-schema/blob/1164987a620f34e142869f3979ca63b186c0a061/schema/systeminfo/systeminfo.schema.json#L19
    UNKNOWN = "N/A"
    EVP1 = "EVP1"
    EVP2 = "EVP2-TB"
    # EVP2 on C8Y not implemented at this time


class StreamStatus(enum.Enum):
    Inactive = "Inactive"
    Active = "Active"
    Transitioning = "..."

    @classmethod
    def from_string(cls, value: str) -> "StreamStatus":
        if value == "Standby":
            return cls.Inactive
        elif value == "Streaming":
            return cls.Active
        elif value == "...":
            return cls.Transitioning

        raise ValueError(value)
