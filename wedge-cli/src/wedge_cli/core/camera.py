import enum
import json
import logging
from base64 import b64decode
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Optional

import qrcode
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

    CONNECTION_STATUS_TIMEOUT = timedelta(seconds=20)

    def __init__(self) -> None:
        self.sensor_state = StreamStatus.Disabled
        self.app_state = ""
        self.deploy_status: dict[str, str] = {}
        self.onwire_schema: Optional[OnWireProtocol] = None
        self.attributes_available = False
        self._last_reception: Optional[datetime] = None

    @property
    def is_ready(self) -> bool:
        return self.onwire_schema is not None and self.attributes_available

    @property
    def connected(self) -> bool:
        if self._last_reception is None:
            return False
        else:
            return (
                datetime.now() - self._last_reception
            ) < self.CONNECTION_STATUS_TIMEOUT

    def process_incoming(self, topic: str, payload: dict[str, Any]) -> None:
        sent_from_camera = False
        if topic == MQTTTopics.ATTRIBUTES.value:
            if self.EA_STATE_TOPIC in payload:
                sent_from_camera = True
                decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
                payload[self.EA_STATE_TOPIC] = decoded

                status = decoded["Status"]
                self.sensor_state = StreamStatus.from_string(status["Sensor"])
                self.app_state = status["ApplicationProcessor"]

            if self.SYSINFO_TOPIC in payload:
                sent_from_camera = True
                sys_info = payload[self.SYSINFO_TOPIC]
                if "protocolVersion" in sys_info:
                    self.onwire_schema = OnWireProtocol(sys_info["protocolVersion"])
                self.attributes_available = True

            if self.DEPLOY_STATUS_TOPIC in payload:
                sent_from_camera = True
                self.deploy_status = payload[self.DEPLOY_STATUS_TOPIC]
                self.attributes_available = True

        if sent_from_camera:
            self._last_reception = datetime.now()
            logger.debug("Incoming on %s: %s", topic, str(payload))


class StreamStatus(enum.Enum):
    Disabled = "Disabled"
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

        return cls.Disabled


class MQTTTopics(enum.Enum):
    ATTRIBUTES = "v1/devices/me/attributes"
    TELEMETRY = "v1/devices/me/telemetry"
    ATTRIBUTES_REQ = "v1/devices/me/attributes/request/+"
    RPC_RESPONSES = "v1/devices/me/rpc/response/+"


def get_qr_object(
    mqtt_host: str, mqtt_port: int, tls_enabled: bool, ntp_server: str, border: int = 5
) -> qrcode.main.QRCode:
    """
    This function generates the QR code object that encodes the connection
    settings for a camera device.

    :param mqtt_host:   Address of MQTT broker host
    :param mqtt_port:   TCP port on which the MQTT broker is listening
    :param tls_enabled: Is TLS enabled?
    :param ntp_server:  NTP server for the camera to get its time synced
    :param border:      size of padding around the QR code
    :return: the QR object containing the code for the camera
    """

    # This verbosity is to blame between types-qrcode and mypy
    # It should be instead: qr_code = qrcode.QRCode(...
    qr_code: qrcode.main.QRCode = qrcode.main.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
    )
    qr_code.add_data(qr_string(mqtt_host, mqtt_port, tls_enabled, ntp_server))
    qr_code.make(fit=True)

    return qr_code


def qr_string(
    mqtt_host: str, mqtt_port: int, tls_enabled: bool, ntp_server: str
) -> str:
    tls_flag = 0 if tls_enabled else 1
    return f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={mqtt_host};H={mqtt_port};t={tls_flag};T={ntp_server};U1FS"
