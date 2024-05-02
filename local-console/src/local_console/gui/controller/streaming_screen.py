from local_console.core.camera import StreamStatus
from local_console.gui.driver import Driver
from local_console.gui.model.streaming_screen import StreamingScreenModel
from local_console.gui.utils.axis_mapping import UnitROI
from local_console.gui.view.streaming_screen.streaming_screen import StreamingScreenView
from pygments.lexers import (
    JsonLexer,
)  # nopycln: import # Required by the screen's KV spec file


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

    def toggle_stream_status(self) -> None:
        camera_status = self.model.stream_status
        if camera_status == StreamStatus.Inactive:
            self.driver.from_sync(self.driver.streaming_rpc_start, self.model.image_roi)
            self.view.ids.stream_image.cancel_roi_draw()
        elif camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)

        self.model.stream_status = StreamStatus.Transitioning

    def set_roi(self, roi: UnitROI) -> None:
        self.model.image_roi = roi

        camera_status = self.model.stream_status
        if camera_status == StreamStatus.Transitioning:
            return

        self.model.stream_status = StreamStatus.Transitioning
        if camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)
