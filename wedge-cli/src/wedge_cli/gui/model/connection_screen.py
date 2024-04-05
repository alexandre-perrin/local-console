import logging

from pydantic import ValidationError
from wedge_cli.core.config import get_config
from wedge_cli.core.schemas import IPAddress
from wedge_cli.core.schemas import MQTTParams
from wedge_cli.gui.model.base_model import BaseScreenModel

logger = logging.getLogger(__name__)


class ConnectionScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.settings_screen.ConnectionScreen.ConnectionScreenView` class.
    """

    def __init__(self) -> None:
        config = get_config()
        # Settings
        self._mqtt_host = config.mqtt.host.ip_value
        self._mqtt_port = str(config.mqtt.port)
        self._ntp_host = "pool.ntp.org"
        # Settings validity
        self._mqtt_host_valid = True
        self._mqtt_port_valid = True
        self._ntp_host_valid = True
        # Connection status
        self._is_connected = False

    def validate_mqtt_host(self) -> bool:
        try:
            IPAddress(ip_value=self.mqtt_host),
        except ValidationError as e:
            logger.warning(f"Validation error of MQTT host: {e}")
            return False
        return True

    @property
    def mqtt_host(self) -> str:
        return self._mqtt_host

    @mqtt_host.setter
    def mqtt_host(self, host: str) -> None:
        self._mqtt_host = host
        self._mqtt_host_valid = self.validate_mqtt_host()
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def mqtt_host_valid(self) -> bool:
        return self._mqtt_host_valid

    def validate_mqtt_port(self) -> bool:
        try:
            MQTTParams(
                host=IPAddress(ip_value="localhost"),
                port=int(self.mqtt_port),
                device_id=None,
            )
        except ValueError as e:
            logger.warning(f"Validation error of MQTT port: {e}")
            return False
        return True

    @property
    def mqtt_port(self) -> str:
        return self._mqtt_port

    @mqtt_port.setter
    def mqtt_port(self, port: str) -> None:
        self._mqtt_port = port
        self._mqtt_port_valid = self.validate_mqtt_port()
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def mqtt_port_valid(self) -> bool:
        return self._mqtt_port_valid

    def validate_ntp_host(self) -> bool:
        try:
            IPAddress(ip_value=self.ntp_host)
        except ValidationError as e:
            logger.warning(f"Validation error of MQTT port: {e}")
            return False
        return True

    @property
    def ntp_host(self) -> str:
        return self._ntp_host

    @ntp_host.setter
    def ntp_host(self, host: str) -> None:
        self._ntp_host = host
        self._ntp_host_valid = self.validate_ntp_host()
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def ntp_host_valid(self) -> bool:
        return self._ntp_host_valid

    @property
    def connected(self) -> bool:
        return self._is_connected

    @connected.setter
    def connected(self, connected: bool) -> None:
        self._is_connected = connected
        self.notify_observers()

    @property
    def is_valid_parameters(self) -> bool:
        return self._mqtt_host_valid and self._mqtt_port_valid and self._ntp_host_valid
