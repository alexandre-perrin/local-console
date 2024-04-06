from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.core.camera import StreamStatus
from wedge_cli.gui.view.base_screen import BaseScreenView
from wedge_cli.gui.view.common.components import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file


class InferenceScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.model_is_changed()

    def toggle_stream_status(self) -> None:
        self.controller.toggle_stream_status()

    def model_is_changed(self) -> None:
        """
        Called whenever any change has occurred in the data model.
        The view in this method tracks these changes and updates the UI
        according to these changes.
        """
        stream_active = self.model.stream_status == StreamStatus.Active

        self.ids.stream_flag.text = self.model.stream_status.value
        self.ids.btn_stream_control.style = (
            "elevated" if not stream_active else "filled"
        )
