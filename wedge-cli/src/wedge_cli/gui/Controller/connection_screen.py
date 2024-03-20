from wedge_cli.core.camera import get_qr_object
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.Model.connection_screen import ConnectionScreenModel
from wedge_cli.gui.Utility.qr import Color
from wedge_cli.gui.Utility.qr import qr_object_as_texture
from wedge_cli.gui.View.ConnectionScreen.connection_screen import ConnectionScreenView
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
        tls_enabled = False
        qr = get_qr_object(
            replace_local_address(self.model.mqtt_host),
            self.model.mqtt_port,
            tls_enabled,
            replace_local_address(self.model.ntp_host),
            border=1,
        )
        background: Color = tuple(
            int(255 * (val * 1.1)) for val in self.view.theme_cls.backgroundColor[:3]
        )
        fill: Color = (0, 0, 0)
        self.view.ids.img_qr_display.texture = qr_object_as_texture(
            qr, background, fill
        )
