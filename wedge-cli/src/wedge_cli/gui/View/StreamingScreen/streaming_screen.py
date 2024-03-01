from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.camera import StreamStatus
from wedge_cli.gui.View.base_screen import BaseScreenView
from wedge_cli.gui.View.common.components import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.View.common.components import ROIState


class StreamingScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.refresh_roi_state(self.ids.stream_image.state)
        self.model_is_changed()

    def toggle_stream_status(self) -> None:
        self.controller.toggle_stream_status()

    def control_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state == ROIState.Disabled:
            # might want to give visual feedback here
            return
        elif roi_state == ROIState.Viewing:
            self.ids.stream_image.start_roi_draw()
        else:
            self.ids.stream_image.cancel_roi_draw()

    def reset_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state != ROIState.Disabled:
            self.ids.stream_image.cancel_roi_draw()
            self.controller.set_roi(self.model.DEFAULT_ROI)

    def refresh_roi_state(self, roi_state: ROIState) -> None:
        # The "Set ROI" button
        self.ids.btn_roi_control.disabled = roi_state == ROIState.Disabled
        if roi_state != ROIState.Disabled:
            if roi_state == ROIState.Viewing:
                self.ids.btn_roi_control.style = "elevated"
            else:
                self.ids.btn_roi_control.style = "filled"

        # The "Reset ROI" button
        self.ids.btn_roi_reset.disabled = roi_state == ROIState.Disabled

    def model_is_changed(self) -> None:
        stream_active = self.model.stream_status == StreamStatus.Active

        self.ids.stream_flag.text = self.model.stream_status.value
        self.ids.btn_stream_control.style = (
            "elevated" if not stream_active else "filled"
        )
