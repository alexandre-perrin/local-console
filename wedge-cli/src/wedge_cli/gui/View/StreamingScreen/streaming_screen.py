from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.View.base_screen import BaseScreenView
from wedge_cli.gui.View.common.components import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file


class StreamingScreenView(BaseScreenView):
    def toggle_stream_status(self) -> None:
        self.controller.set_stream_status(not self.model.stream_status)

    def model_is_changed(self) -> None:
        self.ids.stream_flag.text = "Active" if self.model.stream_status else "Inactive"
