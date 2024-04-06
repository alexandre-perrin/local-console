from wedge_cli.core.config import get_config
from wedge_cli.gui.model.base_model import BaseScreenModel


class ConnectionScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.settings_screen.ConnectionScreen.ConnectionScreenView` class.
    """

    def __init__(self) -> None:
        config = get_config()
        self._mqtt_host = config.mqtt.host.ip_value
        self._mqtt_port = config.mqtt.port
        self._ntp_host = "pool.ntp.org"
        self._is_connected = False

    @property
    def mqtt_host(self) -> str:
        return self._mqtt_host

    @mqtt_host.setter
    def mqtt_host(self, host: str) -> None:
        self._mqtt_host = host
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def mqtt_port(self) -> int:
        return self._mqtt_port

    @mqtt_port.setter
    def mqtt_port(self, port: int) -> None:
        self._mqtt_port = port
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def ntp_host(self) -> str:
        return self._ntp_host

    @ntp_host.setter
    def ntp_host(self, host: str) -> None:
        self._ntp_host = host
        # Maybe commit the new value into the persistent configuration
        self.notify_observers()

    @property
    def connected(self) -> bool:
        return self._is_connected

    @connected.setter
    def connected(self, connected: bool) -> None:
        self._is_connected = connected
        self.notify_observers()
