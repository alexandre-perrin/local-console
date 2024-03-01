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

    def __init__(self) -> None:
        self.sensor_state = StreamStatus.Inactive
        self.app_state = ""

    def process_incoming(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == Agent.ATTRIBUTES_TOPIC:
            if self.EA_STATE_TOPIC in payload:
                decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
                payload[self.EA_STATE_TOPIC] = decoded

                status = decoded["Status"]
                self.sensor_state = StreamStatus.from_string(status["Sensor"])
                self.app_state = status["ApplicationProcessor"]

        logger.critical("Incoming on %s: %s", topic, str(payload))


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
