from kivy.properties import StringProperty
from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.Model.streaming_screen import ROI
from wedge_cli.gui.View.base_screen import BaseScreenView
from wedge_cli.gui.View.common import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file


class StreamingScreenView(BaseScreenView):
    streamed_image = StringProperty("")

    def toggle_stream_status(self) -> None:
        self.controller.set_stream_status(not self.model.stream_status)

    def capture_roi(self) -> None:
        self.ids.stream_image.activate_select_mode()

    def set_roi(self, value: ROI) -> None:
        # crop(x 0 y 0 w 4056 h 3040
        self.controller.set_image_roi(value)

    def model_is_changed(self) -> None:
        self.ids.stream_flag.text = "Active" if self.model.stream_status else "Inactive"
