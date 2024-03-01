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
        stream_active = self.model.stream_status == StreamStatus.Active

        self.ids.stream_flag.text = self.model.stream_status.value
        self.ids.btn_stream_control.style = (
            "elevated" if not stream_active else "filled"
        )
