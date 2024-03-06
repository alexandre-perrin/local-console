import enum
import json
import logging
from base64 import b64decode
from typing import Any
from typing import Optional

from wedge_cli.core.schemas import OnWireProtocol

logger = logging.getLogger(__name__)


class Camera:
    """
    This class is a live, read-only interface to most status
    information that the Camera Firmware reports.
    """

    EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
    SYSINFO_TOPIC = "systemInfo"
    DEPLOY_STATUS_TOPIC = "deploymentStatus"

    def __init__(self) -> None:
        self.sensor_state = StreamStatus.Inactive
        self.app_state = ""
        self.deploy_status: dict[str, str] = {}
        self.onwire_schema: Optional[OnWireProtocol] = None
        self.attributes_available = False

    @property
    def is_ready(self) -> bool:
        return self.onwire_schema is not None and self.attributes_available

    def process_incoming(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == MQTTTopics.ATTRIBUTES.value:
            if self.EA_STATE_TOPIC in payload:
                decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
                payload[self.EA_STATE_TOPIC] = decoded

                status = decoded["Status"]
                self.sensor_state = StreamStatus.from_string(status["Sensor"])
                self.app_state = status["ApplicationProcessor"]

            if self.SYSINFO_TOPIC in payload:
                sys_info = payload[self.SYSINFO_TOPIC]
                self.onwire_schema = OnWireProtocol(sys_info["protocolVersion"])
                self.attributes_available = True

            if self.DEPLOY_STATUS_TOPIC in payload:
                self.deploy_status = payload[self.DEPLOY_STATUS_TOPIC]
                self.attributes_available = True

        logger.debug("Incoming on %s: %s", topic, str(payload))


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


class MQTTTopics(enum.Enum):
    ATTRIBUTES = "v1/devices/me/attributes"
    TELEMETRY = "v1/devices/me/telemetry"
    ATTRIBUTES_REQ = "v1/devices/me/attributes/request/+"
    RPC_RESPONSES = "v1/devices/me/rpc/response/+"
