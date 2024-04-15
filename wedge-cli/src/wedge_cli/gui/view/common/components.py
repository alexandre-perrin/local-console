import enum
import logging
from math import fabs
from pathlib import Path
from typing import Optional

from kivy.core.window import Window
from kivy.graphics import Color
from kivy.graphics import Line
from kivy.graphics.texture import Texture
from kivy.input import MotionEvent
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.uix.image import Image
from kivymd.uix.filemanager import MDFileManager
from wedge_cli.gui.utils.axis_mapping import as_normal_in_set
from wedge_cli.gui.utils.axis_mapping import DEFAULT_ROI
from wedge_cli.gui.utils.axis_mapping import delta
from wedge_cli.gui.utils.axis_mapping import denormalize_in_set
from wedge_cli.gui.view.common.behaviors import HoverBehavior

logger = logging.getLogger(__name__)


class ROIState(enum.Enum):
    Disabled = enum.auto()
    Enabled = enum.auto()
    PickingStartPoint = enum.auto()
    PickingEndPoint = enum.auto()
    Viewing = enum.auto()


class ImageWithROI(Image, HoverBehavior):
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

    def start_roi_draw(self) -> None:
        if self.state == ROIState.Disabled:
            logger.critical("Image not yet loaded! Aborting ROI")
            return

        self.state = ROIState.PickingStartPoint
        self.clear_roi()

    def cancel_roi_draw(self) -> None:
        self.state = ROIState.Enabled
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

    def on_enter(self) -> None:
        if self.state in (
            ROIState.PickingStartPoint,
            ROIState.PickingEndPoint,
        ) and self.point_is_in_subregion(self.current_point):
            Window.set_system_cursor("crosshair")
            if self.state == ROIState.PickingEndPoint:
                self.rect_end = self.current_point
                self.draw_rectangle()
        else:
            Window.set_system_cursor("arrow")

    def on_leave(self) -> None:
        Window.set_system_cursor("arrow")

    def draw_rectangle(self) -> None:
        start = (
            min(self.rect_end[0], self.rect_start[0]),
            min(self.rect_end[1], self.rect_start[1]),
        )
        size = (
            int(fabs(self.rect_end[0] - self.rect_start[0])),
            int(fabs(self.rect_end[1] - self.rect_start[1])),
        )
        self.refresh_rectangle(start, size)

    def refresh_rectangle(self, start: tuple[int, int], size: tuple[int, int]) -> None:
        self._clear_rect()
        if self.state in (ROIState.PickingEndPoint, ROIState.Viewing):
            with self.canvas:
                Color(1, 0, 0, 1)
                self.rect_line = Line(rectangle=[*start, size[0], size[1]], width=1.5)

    def update_image_data(self, incoming_file: Path) -> None:
        self.source = str(incoming_file)

    def prime_for_roi(self, _texture: Texture) -> None:
        if self.state == ROIState.Disabled:
            self.state = ROIState.Enabled
        self.update_norm_subregion()

    def update_roi(self) -> None:
        self.update_norm_subregion()
        i_start, i_size = self.roi
        if sum(i_size) > 0:
            # denormalize to widget's unit coordinates
            w_start: tuple[float, float] = (
                denormalize_in_set(i_start[0], self._active_subregion[0]),
                denormalize_in_set(i_start[1], self._active_subregion[1]),
            )
            w_size: tuple[float, float] = (
                denormalize_in_set(i_size[0], (0, delta(self._active_subregion[0]))),
                denormalize_in_set(i_size[1], (0, delta(self._active_subregion[1]))),
            )
            # denormalize to pixel coordinates
            new_width, new_height = self.size
            start = (
                int(denormalize_in_set(w_start[0], (0, new_width))),
                int(denormalize_in_set(w_start[1], (0, new_height))),
            )
            size = (
                int(denormalize_in_set(w_size[0], (0, new_width))),
                int(denormalize_in_set(w_size[1], (0, new_height))),
            )
            self.refresh_rectangle(start, size)

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

    def point_is_in_subregion(self, pos: tuple[int, int]) -> bool:
        if all(coord == 0 for axis in self._active_subregion for coord in axis):
            return False
        if self.collide_point(*pos):
            # Not only must the cursor be within the widget,
            # it must also be within the subregion of the image
            normalized = [
                as_normal_in_set(pos[dim], (0, self.size[dim])) for dim in (0, 1)
            ]
            if all(
                self._active_subregion[dim][0]
                <= normalized[dim]
                <= self._active_subregion[dim][1]
                for dim in (0, 1)
            ):
                return True
        return False


class FileManager(MDFileManager):
    _opening_path = StringProperty(str(Path.cwd()))

    def refresh_opening_path(self) -> None:
        cur = Path(self.current_path)
        if cur.is_dir():
            self._opening_path = str(cur)
        else:
            self._opening_path = str(cur.parent)

    def open(self) -> None:
        self.show(self._opening_path)
