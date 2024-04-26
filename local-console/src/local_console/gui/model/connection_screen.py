import logging
import re

from local_console.core.config import get_config
from local_console.core.schemas.schemas import IPAddress
from local_console.core.schemas.schemas import MQTTParams
from local_console.gui.model.base_model import BaseScreenModel
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.local_network import is_valid_host
from pydantic import ValidationError
from pydantic.networks import IPvAnyAddress

logger = logging.getLogger(__name__)


class ConnectionScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.settings_screen.ConnectionScreen.ConnectionScreenView` class.
    """

    MAX_LEN_PORT = int(5)
    MAX_LEN_IP_ADDRESS = int(39)
    MAX_LEN_DOMAIN_NAME = int(64)

    def __init__(self) -> None:
        config = get_config()
        # Settings
        self._local_ip = get_my_ip_by_routing()
        self._mqtt_host = config.mqtt.host.ip_value
        self._mqtt_port = str(config.mqtt.port)
        self._ntp_host = "pool.ntp.org"
        self._ip_address = ""
        self._subnet_mask = ""
        self._gateway = ""
        self._dns_server = ""
        # Settings validity
        self._mqtt_host_error = False
        self._mqtt_port_error = False
        self._ntp_host_error = False
        self._ip_address_error = False
        self._subnet_mask_error = False
        self._gateway_error = False
        self._dns_server_error = False
        # Connection status
        self._is_connected = False
        # Warning message
        self._warning_message = ""

    def validate_hostname(self, host: str) -> bool:
        try:
            IPAddress(ip_value=host),
        except ValidationError as e:
            logger.warning(f"Validation error of hostname: {e}")
            return False

        if not is_valid_host(host):
            return False
        return True

    def validate_ip_address(self, ip: str) -> bool:
        try:
            IPvAnyAddress(ip)
        except ValueError as e:
            logger.warning(f"Validation error of IP address: {e}")
            return False
        return True

    def validate_all_settings(self) -> None:
        # Validate all settings and set color of invalid cell
        self._mqtt_host_error = not self.validate_hostname(self.mqtt_host)
        self._mqtt_port_error = not self.validate_mqtt_port()
        self._ntp_host_error = not self.validate_hostname(self.ntp_host)
        if not self.ip_address:
            self._ip_address_error = False
        else:
            self._ip_address_error = not self.validate_ip_address(self.ip_address)
        if not self.subnet_mask:
            self._subnet_mask_error = False
        else:
            self._subnet_mask_error = not self.validate_ip_address(self.subnet_mask)
        if not self.gateway:
            self._gateway_error = False
        else:
            self._gateway_error = not self.validate_ip_address(self.gateway)
        if not self.dns_server:
            self._dns_server_error = False
        else:
            self._dns_server_error = not self.validate_ip_address(self.dns_server)

    def ganerate_warning_message(self) -> str:
        warning_message = ""
        if self._mqtt_host_error:
            warning_message += "\n- MQTT host address"
        if self._mqtt_port_error:
            warning_message += "\n- MQTT port"
        if self._ntp_host_error:
            warning_message += "\n- NTP server address"
        if self._ip_address_error:
            warning_message += "\n- IP Address"
        if self._subnet_mask_error:
            warning_message += "\n- Subnet Mask"
        if self._gateway_error:
            warning_message += "\n- Gateway"
        if self._dns_server:
            warning_message += "\n- DNS server"
        if warning_message != "":
            warning_message = "Warning, invalid parameters:" + warning_message
        return warning_message

    # Local IP Address
    @property
    def local_ip(self) -> str:
        return self._local_ip

    @local_ip.setter
    def local_ip(self, ip: str) -> None:
        if ip == "":
            # In case of no connectivity
            self._warning_message = (
                "Warning, No Local IP Address.\nPlease check connectivity."
            )
            self._local_ip = ip
            self.notify_observers()
            return

        # Validate all settings to set color of invalid cell
        self.validate_all_settings()

        # Generate warning message of invalid parameter
        warning_message = self.ganerate_warning_message()

        # Add warning message of local ip updated
        if self._local_ip != ip:
            if warning_message != "":
                warning_message += "\n"
            warning_message += "Warning, Local IP Address is updated."

        # Set warning message if any warning to display
        if warning_message != "":
            self._warning_message = warning_message

        self._local_ip = ip
        self.notify_observers()

    # MQTT host address
    @property
    def mqtt_host(self) -> str:
        return self._mqtt_host

    @mqtt_host.setter
    def mqtt_host(self, host: str) -> None:
        if len(host) <= self.MAX_LEN_DOMAIN_NAME:
            self._mqtt_host = host
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def mqtt_host_error(self) -> bool:
        return self._mqtt_host_error

    # MQTT port
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
        self._mqtt_port = re.sub(r"\D", "", port)[: self.MAX_LEN_PORT]
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def mqtt_port_error(self) -> bool:
        return self._mqtt_port_error

    # NTP server address
    @property
    def ntp_host(self) -> str:
        return self._ntp_host

    @ntp_host.setter
    def ntp_host(self, host: str) -> None:
        if len(host) <= self.MAX_LEN_DOMAIN_NAME:
            self._ntp_host = host
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def ntp_host_error(self) -> bool:
        return self._ntp_host_error

    # IP Address (for Static IP)
    @property
    def ip_address(self) -> str:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, ip: str) -> None:
        if len(ip) <= self.MAX_LEN_IP_ADDRESS:
            self._ip_address = ip
        self.notify_observers()

    @property
    def ip_address_error(self) -> bool:
        return self._ip_address_error

    # Subnet Mask (for Static IP)
    @property
    def subnet_mask(self) -> str:
        return self._subnet_mask

    @subnet_mask.setter
    def subnet_mask(self, mask: str) -> None:
        if len(mask) <= self.MAX_LEN_IP_ADDRESS:
            self._subnet_mask = mask
        self.notify_observers()

    @property
    def subnet_mask_error(self) -> bool:
        return self._subnet_mask_error

    # Gateway (for Static IP)
    @property
    def gateway(self) -> str:
        return self._gateway

    @gateway.setter
    def gateway(self, gateway: str) -> None:
        if len(gateway) <= self.MAX_LEN_IP_ADDRESS:
            self._gateway = gateway
        self.notify_observers()

    @property
    def gateway_error(self) -> bool:
        return self._gateway_error

    # DNS server (for Static IP)
    @property
    def dns_server(self) -> str:
        return self._dns_server

    @dns_server.setter
    def dns_server(self, server: str) -> None:
        if len(server) <= self.MAX_LEN_IP_ADDRESS:
            self._dns_server = server
        self.notify_observers()

    @property
    def dns_server_error(self) -> bool:
        return self._dns_server_error

    # Others
    @property
    def connected(self) -> bool:
        return self._is_connected

    @connected.setter
    def connected(self, connected: bool) -> None:
        self._is_connected = connected
        self.notify_observers()

    @property
    def warning_message(self) -> str:
        return self._warning_message

    @warning_message.setter
    def warning_message(self, warning: str) -> None:
        self._warning_message = warning
        self.notify_observers()
