from wedge_cli.core.camera import get_qr_object
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.model.connection_screen import ConnectionScreenModel
from wedge_cli.gui.utils.qr import Color
from wedge_cli.gui.utils.qr import qr_object_as_texture
from wedge_cli.gui.view.ConnectionScreen.connection_screen import ConnectionScreenView
from wedge_cli.utils.local_network import get_my_ip_by_routing
from wedge_cli.utils.local_network import replace_local_address


class ConnectionScreenController:
    """
    The `ConnectionScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ConnectionScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = ConnectionScreenView(controller=self, model=self.model)

    def get_view(self) -> ConnectionScreenView:
        return self.view

    def qr_generate(self) -> None:
        # Get the local IP since it might be updated.
        self.model.local_ip = get_my_ip_by_routing()
        mqtt_port = int(self.model.mqtt_port) if self.model.mqtt_port != "" else None
        tls_enabled = False
        qr = get_qr_object(
            replace_local_address(self.model.mqtt_host),
            mqtt_port,
            tls_enabled,
            replace_local_address(self.model.ntp_host),
            self.model.ip_address,
            self.model.subnet_mask,
            self.model.gateway,
            self.model.dns_server,
            border=4,
        )
        background: Color = tuple(
            int(255 * (val * 1.1)) for val in self.view.theme_cls.backgroundColor[:3]
        )
        fill: Color = (0, 0, 0)
        self.view.ids.img_qr_display.texture = qr_object_as_texture(
            qr, background, fill
        )
