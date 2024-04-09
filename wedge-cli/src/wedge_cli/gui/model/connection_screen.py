import logging

from pydantic import ValidationError
from pydantic.networks import IPvAnyAddress
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

    MAX_STRING_LENGTH = int(39)

    def __init__(self) -> None:
        config = get_config()
        # Settings
        self._mqtt_host = config.mqtt.host.ip_value
        self._mqtt_port = str(config.mqtt.port)
        self._ntp_host = "pool.ntp.org"
        self._ip_address = ""
        self._subnet_mask = ""
        self._gateway = ""
        self._dns_server = ""
        # Settings validity
        self._mqtt_host_valid = True
        self._mqtt_port_valid = True
        self._ntp_host_valid = True
        self._subnet_mask_valid = True
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
    def ip_address(self) -> str:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, ip: str) -> None:
        # Limit the length in the same way as the Setup Enrollment on the Console
        if len(ip) <= self.MAX_STRING_LENGTH:
            self._ip_address = ip
        self.notify_observers()

    def validate_subnet_mask(self) -> bool:
        try:
            IPvAnyAddress(self.subnet_mask)
        except ValueError as e:
            logger.warning(f"Validation error of Subnet Mask: {e}")
            return False
        return True

    @property
    def subnet_mask(self) -> str:
        return self._subnet_mask

    @subnet_mask.setter
    def subnet_mask(self, mask: str) -> None:
        # Limit the length in the same way as the Setup Enrollment on the Console
        if len(mask) <= self.MAX_STRING_LENGTH:
            self._subnet_mask = mask
        self._subnet_mask_valid = self.validate_subnet_mask()
        self.notify_observers()

    @property
    def subnet_mask_valid(self) -> bool:
        return self._subnet_mask_valid

    @property
    def gateway(self) -> str:
        return self._gateway

    @gateway.setter
    def gateway(self, gateway: str) -> None:
        # Limit the length in the same way as the Setup Enrollment on the Console
        if len(gateway) <= self.MAX_STRING_LENGTH:
            self._gateway = gateway
        self.notify_observers()

    @property
    def dns_server(self) -> str:
        return self._dns_server

    @dns_server.setter
    def dns_server(self, server: str) -> None:
        # Limit the length in the same way as the Setup Enrollment on the Console
        if len(server) <= self.MAX_STRING_LENGTH:
            self._dns_server = server
        self.notify_observers()

    @property
    def connected(self) -> bool:
        return self._is_connected

    @connected.setter
    def connected(self, connected: bool) -> None:
        self._is_connected = connected
        self.notify_observers()

    @property
    def is_valid_parameters(self) -> bool:
        return (
            self._mqtt_host_valid
            and self._mqtt_port_valid
            and self._ntp_host_valid
            and self._subnet_mask_valid
        )
