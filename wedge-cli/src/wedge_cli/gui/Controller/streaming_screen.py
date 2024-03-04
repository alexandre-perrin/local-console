from pygments.lexers import (
    JsonLexer,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.Model.streaming_screen import StreamingScreenModel
from wedge_cli.gui.Utility.axis_mapping import UnitROI
from wedge_cli.gui.View.StreamingScreen.streaming_screen import StreamingScreenView


class StreamingScreenController:
    """
    The `StreamingScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: StreamingScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = StreamingScreenView(controller=self, model=self.model)

    def get_view(self) -> StreamingScreenView:
        return self.view

    def set_stream_status(self, value: bool) -> None:
        if value:
            self.driver.from_sync(self.driver.streaming_rpc_start)
        else:
            self.driver.from_sync(self.driver.streaming_rpc_stop)

        # TODO do this based on some event emitted by the camera
        self.model.stream_status = value

    def set_roi(self, roi: UnitROI) -> None:
        self.model.image_roi = roi
