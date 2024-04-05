from pygments.lexers import (
    JsonLexer,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.core.camera import StreamStatus
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.model.inference_screen import InferenceScreenModel
from wedge_cli.gui.view.InferenceScreen.inference_screen import InferenceScreenView


class InferenceScreenController:
    """
    The `InferenceScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: InferenceScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = InferenceScreenView(controller=self, model=self.model)

    def get_view(self) -> InferenceScreenView:
        return self.view

    def toggle_stream_status(self) -> None:
        camera_status = self.model.stream_status
        if camera_status == StreamStatus.Inactive:
            self.driver.from_sync(self.driver.streaming_rpc_start)
        elif camera_status == StreamStatus.Active:
            self.driver.from_sync(self.driver.streaming_rpc_stop)

        self.model.stream_status = StreamStatus.Transitioning
