import enum
import logging
from math import fabs
from pathlib import Path
from typing import Optional

from kivy.core.window import Window
from kivy.graphics import Color
from kivy.graphics import Line
from kivy.input import MotionEvent
from kivy.properties import ObjectProperty
from kivy.uix.image import Image
from wedge_cli.gui.Utility.axis_mapping import as_normal_in_set
from wedge_cli.gui.Utility.axis_mapping import DEFAULT_ROI

logger = logging.getLogger(__name__)




class ROIState(enum.Enum):
    Disabled = enum.auto()
    Viewing = enum.auto()
    PickingStartPoint = enum.auto()
    PickingEndPoint = enum.auto()


class ImageWithROI(Image):
    roi = ObjectProperty(DEFAULT_ROI)
    state = ObjectProperty(ROIState.Disabled)

    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)
        self.roi_start: tuple[float, float] = (0, 0)
        self.rect_start: tuple[int, int] = (0, 0)
        self.rect_end: tuple[int, int] = (0, 0)
        self.rect_line: Optional[Line] = None
        # Should be of type UnitROI but Python tuples are immutable
        # and we need to assign to the tuple elements.
        self._active_subregion: list[tuple[float, float]] = [(0, 0), (0, 0)]
        Window.bind(mouse_pos=self.on_mouse_pos)

    def activate_select_mode(self) -> None:
        if self.state == ROIState.Disabled:
            logger.critical("Image not yet loaded! Aborting ROI")
            return

        self.state = ROIState.PickingStartPoint
        self.clear_roi()

    def clear_roi(self) -> None:
        self._clear_rect()
        self.roi_start = (0, 0)
        self.rect_start = (0, 0)
        self.rect_end = (0, 0)

    def _clear_rect(self) -> None:
        if self.rect_line:
            self.canvas.remove(self.rect_line)
            self.rect_line = None

    def on_touch_down(self, touch: MotionEvent) -> bool:
        if self.state == ROIState.PickingStartPoint and self.point_is_in_subregion(
            touch.pos
        ):
            self.rect_start = touch.pos
            # normalize coordinate within the widget space
            w_roi_start: tuple[float, float] = (
                as_normal_in_set(touch.x, (0, self.size[0])),
                as_normal_in_set(touch.y, (0, self.size[1])),
            )
            # normalize coordinate within the image space
            self.roi_start = (
                as_normal_in_set(w_roi_start[0], self._active_subregion[0]),
                as_normal_in_set(w_roi_start[1], self._active_subregion[1]),
            )
            self.state = ROIState.PickingEndPoint
            return True  # to consume the event and not propagate it further

        elif self.state == ROIState.PickingEndPoint and self.point_is_in_subregion(
            touch.pos
        ):
            self.rect_end = touch.pos
            self.draw_rectangle()
            self.state = ROIState.Viewing
            # normalize coordinate within the widget space
            w_roi_end: tuple[float, float] = (
                as_normal_in_set(touch.x, (0, self.size[0])),
                as_normal_in_set(touch.y, (0, self.size[1])),
            )
            # normalize coordinate within the image space
            roi_end = (
                as_normal_in_set(w_roi_end[0], self._active_subregion[0]),
                as_normal_in_set(w_roi_end[1], self._active_subregion[1]),
            )

            # these are in the image's unit coordinate system
            i_roi_min = (
                min(self.roi_start[0], roi_end[0]),
                min(self.roi_start[1], roi_end[1]),
            )
            i_rect_size = (
                fabs(self.roi_start[0] - roi_end[0]),
                fabs(self.roi_start[1] - roi_end[1]),
            )
            self.roi_start = i_roi_min
            self.roi = (self.roi_start, i_rect_size)
            return True  # to consume the event and not propagate it further

        return bool(super().on_touch_down(touch))

    def on_mouse_pos(self, window: Window, pos: tuple[int, int]) -> None:
        if self.state in (
            ROIState.PickingStartPoint,
            ROIState.PickingEndPoint,
        ) and self.point_is_in_subregion(pos):
            window.set_system_cursor("crosshair")
            if self.state == ROIState.PickingEndPoint:
                self.rect_end = pos
                self.draw_rectangle()
        else:
            window.set_system_cursor("arrow")

    def draw_rectangle(self) -> None:
        rect_size = (
            int(fabs(self.rect_end[0] - self.rect_start[0])),
            int(fabs(self.rect_end[1] - self.rect_start[1])),
        )
        r_start = (
            min(self.rect_end[0], self.rect_start[0]),
            min(self.rect_end[1], self.rect_start[1]),
        )
        self._clear_rect()
        with self.canvas:
            Color(1, 0, 0, 1)
            self.rect_line = Line(
                rectangle=[*r_start, rect_size[0], rect_size[1]], width=1.5
            )

    def update_image_data(self, incoming_file: Path) -> None:
        self.source = str(incoming_file)

    def update_norm_subregion(self) -> None:
        if self.state == ROIState.Disabled:
            return

        image_size_map = self.get_norm_image_size()
        widget_size = self.size
        limits = [(0.0, 0.0), (0.0, 0.0)]
        for dim in (0, 1):
            min_dim = as_normal_in_set(
                (widget_size[dim] - image_size_map[dim]) / 2, (0, widget_size[dim])
            )
            max_dim = as_normal_in_set(
                (widget_size[dim] + image_size_map[dim]) / 2, (0, widget_size[dim])
            )
            limits[dim] = (min_dim, max_dim)

        self._active_subregion = limits
