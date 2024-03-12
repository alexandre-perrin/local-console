import logging

from kivy.uix.widget import Widget
from pydantic import ValidationError
from wedge_cli.core.schemas import IPAddress
from wedge_cli.core.schemas import MQTTParams
from wedge_cli.gui.View.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class ConnectionScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.model_is_changed()

    def validate_mqtt_host(self, widget: Widget, text: str) -> None:
        try:
            MQTTParams(
                host=IPAddress(ip_value=text), port=self.model.mqtt_port, device_id=None
            )
            widget.error = False
            self.model.mqtt_host = text
        except ValidationError as e:
            widget.error = True
            logger.warning(f"Validation error of MQTT host {widget}: {e}")

    def validate_mqtt_port(self, widget: Widget, text: str) -> None:
        try:
            MQTTParams(
                host=IPAddress(ip_value=self.model.mqtt_host),
                port=int(text),
                device_id=None,
            )
            widget.error = False
            self.model.mqtt_port = int(text)
        except ValueError:
            widget.error = True
        except ValidationError as e:
            widget.error = True
            logger.warning(f"Validation error of MQTT port {widget}: {e}")

    def validate_ntp_port(self, widget: Widget, text: str) -> None:
        try:
            IPAddress(ip_value=text)
            widget.error = False
            self.model.ntp_host = text
        except ValidationError as e:
            widget.error = True
            logger.warning(f"Validation error of NTP host {widget}: {e}")

    def model_is_changed(self) -> None:
        self.ids.lbl_conn_status.text = (
            "Connected [No TLS]" if self.model.connected else "Disconnected"
        )
        if not self.ids.txt_mqtt_host.text:
            self.ids.txt_mqtt_host.text = self.model.mqtt_host
        if not self.ids.txt_mqtt_port.text:
            self.ids.txt_mqtt_port.text = str(self.model.mqtt_port)
        if not self.ids.txt_ntp_host.text:
            self.ids.txt_ntp_host.text = self.model.ntp_host
