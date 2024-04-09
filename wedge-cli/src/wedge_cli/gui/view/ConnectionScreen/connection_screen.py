import logging

from kivy.uix.widget import Widget
from wedge_cli.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class ConnectionScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.model_is_changed()

    def validate_mqtt_host(self, widget: Widget, text: str) -> None:
        self.model.mqtt_host = text
        widget.error = not self.model.mqtt_host_valid

    def validate_mqtt_port(self, widget: Widget, text: str) -> None:
        self.model.mqtt_port = text
        widget.error = not self.model.mqtt_port_valid

    def validate_ntp_host(self, widget: Widget, text: str) -> None:
        self.model.ntp_host = text
        widget.error = not self.model.ntp_host_valid

    def validate_ip_address(self, widget: Widget, text: str) -> None:
        self.model.ip_address = text
        # no validation in the same way as the Setup Enrollment on the Console

    def validate_subnet_mask(self, widget: Widget, text: str) -> None:
        self.model.subnet_mask = text
        widget.error = not self.model.subnet_mask_valid

    def validate_gateway(self, widget: Widget, text: str) -> None:
        self.model.gateway = text
        # no validation in the same way as the Setup Enrollment on the Console

    def validate_dns_server(self, widget: Widget, text: str) -> None:
        self.model.dns_server = text
        # no validation in the same way as the Setup Enrollment on the Console

    def model_is_changed(self) -> None:
        if self.model.is_valid_parameters:
            self.enable_generate_qr()
        else:
            self.disable_generate_qr()

        self.ids.lbl_conn_status.text = (
            "Connected [No TLS]" if self.model.connected else "Disconnected"
        )
        self.ids.txt_mqtt_host.text = self.model.mqtt_host
        self.ids.txt_mqtt_port.text = self.model.mqtt_port
        self.ids.txt_ntp_host.text = self.model.ntp_host
        self.ids.txt_ip_address.text = self.model.ip_address
        self.ids.txt_subnet_mask.text = self.model.subnet_mask
        self.ids.txt_gateway.text = self.model.gateway
        self.ids.txt_dns_server.text = self.model.dns_server

    def enable_generate_qr(self) -> None:
        self.ids.btn_qr_gen.disabled = False

    def disable_generate_qr(self) -> None:
        self.ids.btn_qr_gen.disabled = True
