from pygments.lexers import (
    JsonLexer,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.core.camera import StreamStatus
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

        camera_status = self.driver.camera_state.sensor_state
        if camera_status == StreamStatus.Transitioning:
            return

        self.model.stream_status = StreamStatus.Transitioning
        if camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)
