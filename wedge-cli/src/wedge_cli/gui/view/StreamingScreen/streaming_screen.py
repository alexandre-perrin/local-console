from kivy.metrics import dp
from kivy.uix.codeinput import (
    CodeInput,
)  # nopycln: import # Required by the screen's KV spec file
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.snackbar import MDSnackbarButtonContainer
from kivymd.uix.snackbar import MDSnackbarCloseButton
from kivymd.uix.snackbar import MDSnackbarSupportingText
from wedge_cli.core.camera import StreamStatus
from wedge_cli.gui.utils.axis_mapping import DEFAULT_ROI
from wedge_cli.gui.utils.axis_mapping import pixel_roi_from_normals
from wedge_cli.gui.view.base_screen import BaseScreenView
from wedge_cli.gui.view.common.components import (
    ImageWithROI,
)  # nopycln: import # Required by the screen's KV spec file
from wedge_cli.gui.view.common.components import ROIState


class StreamingScreenView(BaseScreenView):
    def entry_actions(self) -> None:
        self.refresh_roi_state(self.ids.stream_image.state)
        self.model_is_changed()

    def toggle_stream_status(self) -> None:
        self.controller.toggle_stream_status()

    def control_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state == ROIState.Disabled:
            inform_roi_is_disabled()
        elif roi_state == ROIState.Enabled:
            self.ids.stream_image.start_roi_draw()
        else:
            self.ids.stream_image.cancel_roi_draw()

    def reset_roi(self) -> None:
        roi_state: ROIState = self.ids.stream_image.state
        if roi_state != ROIState.Disabled:
            self.ids.stream_image.cancel_roi_draw()
            self.controller.set_roi(DEFAULT_ROI)
        else:
            inform_roi_is_disabled()

    def refresh_roi_state(self, roi_state: ROIState) -> None:
        # The "Set ROI" button
        self.ids.btn_roi_control.disabled = roi_state == ROIState.Disabled
        if roi_state != ROIState.Disabled:
            if roi_state in (ROIState.Enabled, ROIState.Viewing):
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

        (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(
            self.model.image_roi
        )
        self.ids.lbl_roi_h_offset.text = str(h_offset)
        self.ids.lbl_roi_h_size.text = str(h_size)
        self.ids.lbl_roi_v_offset.text = str(v_offset)
        self.ids.lbl_roi_v_size.text = str(v_size)


def inform_roi_is_disabled() -> None:
    MDSnackbar(
        MDSnackbarSupportingText(
            text="Cannot set ROI without having received a camera frame",
        ),
        MDSnackbarButtonContainer(
            MDSnackbarCloseButton(
                icon="close",
            ),
            pos_hint={"center_y": 0.5},
        ),
        y=dp(24),
        orientation="horizontal",
        pos_hint={"center_x": 0.5},
        size_hint_x=0.5,
    ).open()
