import enum
import logging
import re
from math import fabs
from pathlib import Path
from typing import Any
from typing import Optional

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color
from kivy.graphics import Line
from kivy.graphics.texture import Texture
from kivy.input import MotionEvent
from kivy.properties import NumericProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.uix.codeinput import CodeInput
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.tooltip import MDTooltip
from wedge_cli.gui.utils.axis_mapping import as_normal_in_set
from wedge_cli.gui.utils.axis_mapping import DEFAULT_ROI
from wedge_cli.gui.utils.axis_mapping import delta
from wedge_cli.gui.utils.axis_mapping import denormalize_in_set
from wedge_cli.gui.utils.axis_mapping import get_dead_zone_within_image
from wedge_cli.gui.utils.axis_mapping import get_dead_zone_within_widget
from wedge_cli.gui.utils.axis_mapping import get_normalized_center_subregion
from wedge_cli.gui.utils.axis_mapping import snap_point_in_deadzone
from wedge_cli.gui.view.common.behaviors import HoverBehavior

logger = logging.getLogger(__name__)


class ROIState(enum.Enum):
    Disabled = enum.auto()
    Enabled = enum.auto()
    PickingStartPoint = enum.auto()
    PickingEndPoint = enum.auto()
    Viewing = enum.auto()


class ImageWithROI(Image, HoverBehavior):
    # Read-only properties
    roi = ObjectProperty(DEFAULT_ROI)
    state = ObjectProperty(ROIState.Disabled)

    # Widget configuration properties
    dead_zone_px = NumericProperty(20)

    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)
        self.roi_start: tuple[float, float] = (0, 0)
        self.rect_start: tuple[int, int] = (0, 0)
        self.rect_end: tuple[int, int] = (0, 0)
        self.rect_line: Optional[Line] = None
        # Should be of type UnitROI but Python tuples are immutable
        # and we need to assign to the tuple elements.
        self._active_subregion: list[tuple[float, float]] = [(0, 0), (0, 0)]
        # https://www.reddit.com/r/kivy/comments/16qftb0/memory_leak_with_images/
        self.nocache = True
        self._dead_zone_in_image: list[tuple[float, float]] = [(0, 0), (0, 0)]
        self._dead_zone_in_widget: list[tuple[float, float]] = [(0, 0), (0, 0)]

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
            normalized_roi_start = (
                as_normal_in_set(w_roi_start[0], self._active_subregion[0]),
                as_normal_in_set(w_roi_start[1], self._active_subregion[1]),
            )
            self.roi_start = snap_point_in_deadzone(
                normalized_roi_start, self._dead_zone_in_image
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
            normalized_roi_end = (
                as_normal_in_set(w_roi_end[0], self._active_subregion[0]),
                as_normal_in_set(w_roi_end[1], self._active_subregion[1]),
            )
            roi_end = snap_point_in_deadzone(
                normalized_roi_end, self._dead_zone_in_image
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

        image_size = self.get_norm_image_size()
        widget_size = self.size
        active_subregion = get_normalized_center_subregion(image_size, widget_size)
        self._active_subregion = active_subregion
        self.update_dead_zone(image_size, widget_size, active_subregion)

    def update_dead_zone(
        self,
        image_size: tuple[int, int],
        widget_size: tuple[int, int],
        active_subregion: list[tuple[float, float]],
    ) -> None:
        assert self.state != ROIState.Disabled
        dead_subregion_w = get_dead_zone_within_widget(
            self.dead_zone_px, image_size, widget_size
        )
        dead_subregion_i = get_dead_zone_within_image(
            dead_subregion_w, active_subregion
        )
        self._dead_zone_in_widget = dead_subregion_w
        self._dead_zone_in_image = dead_subregion_i

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


class FocusText(MDTextField):
    write_tab = False


class GUITooltip(MDTooltip):
    def on_long_touch(self, *args: Any) -> None:
        """
        Implemented so that the function signature matches the
        spec from the MDTooltip documentation. The original signature,
        coming from KivyMD's TouchBehavior, includes mandatory 'touch'
        argument, which seems to be at odds with base Kivy's event
        dispatch signature.
        """

    def on_double_tap(self, *args: Any) -> None:
        pass  # Same as above

    def on_triple_tap(self, *args: Any) -> None:
        pass  # Same as above


class PathSelectorCombo(MDBoxLayout):
    name = StringProperty("Path")
    """
    Holds the descriptive text of the label for user identification

    :attr:`descriptor` is an :class:`~kivy.properties.StringProperty`
    and defaults to `path`.
    """

    icon = StringProperty("file-cog")
    """
    Holds the name of the icon from the Material Design lib that should
    be rendered in the button that opens the associated file selector view.

    :attr:`icon` is an :class:`~kivy.properties.StringProperty`
    and defaults to `file-cog`.
    """

    path = StringProperty("")
    """
    Holds the current value of the path

    :attr:`path` is an :class:`~kivy.properties.StringProperty`
    and defaults to `""`.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Other MDFileManager properties are to be
        # assigned directly to self.file_manager
        self.file_manager = FileManager(exit_manager=self.exit_manager)

    def accept_path(self, path: str) -> None:
        self.path = path

    def open_manager(self) -> None:
        self.file_manager.open()

    def exit_manager(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.file_manager.close()
        self.file_manager.refresh_opening_path()


class NumberInputField(MDTextField):
    """
    It is an MDTextField that only accepts digits,
    ignoring any other character type.
    """

    pat = re.compile(r"\D")

    def insert_text(self, incoming_char: str, from_undo: bool = False) -> Any:
        s = re.sub(self.pat, "", incoming_char)
        return super().insert_text(s, from_undo=from_undo)


class FileSizeCombo(MDBoxLayout):
    """
    Widget group that provides user-friendly input
    of a file size quantity, with the result in
    bytes given on the 'value' property.
    """

    label = StringProperty("Max size:")
    """
    Sets the label that identifies the widget group to the user

    :attr:`label` is an :class:`~kivy.properties.StringProperty`
    and defaults to `Max size:`.
    """

    value = NumericProperty(0)
    """
    Contains the file size in bytes equivalent to the user
    input values in the widget group.

    :attr:`value` is an :class:`~kivy.properties.NumericProperty`
    and defaults to `0`.
    """

    cool_off_ms = NumericProperty(2000)
    """
    Specifies the input value cool-off period before updating
    the 'value' property.

    :attr:`value` is an :class:`~kivy.properties.NumericProperty`
    and defaults to `0`.
    """

    _factors = {"kB": 2**10, "MB": 2**20, "GB": 2**30}
    _spec = StringProperty("10")
    _selected_unit = StringProperty("MB")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.validation_clock: Optional[Clock] = None
        menu_items = [
            {
                "text": unit,
                "on_release": lambda x=unit: self.set_unit(x),
            }
            for unit in self._factors.keys()
        ]
        self.menu = MDDropdownMenu(
            items=menu_items,
            position="bottom",
        )
        self.update_value()

    def open_menu(self, widget: MDDropDownItem) -> None:
        self.menu.caller = widget
        self.menu.open()

        if self.validation_clock:
            # Previous cool-off was not done, so cancel it
            self.validation_clock.cancel()

    def set_unit(self, unit_item: str) -> None:
        self._selected_unit = unit_item
        self.menu.dismiss()
        self._schedule_validation()

    def set_spec(self, widget: NumberInputField, text: str) -> None:
        self._spec = text
        self._schedule_validation()

    def _schedule_validation(self) -> None:
        if not self.validation_clock:
            # First time, instantiate cool-off clock
            self.validation_clock = Clock.schedule_once(
                lambda _dt: self.update_value(), self.cool_off_ms / 1000
            )
        else:
            # Previous cool-off was not done, so cancel it
            self.validation_clock.cancel()

        # Start input value cool-off before updating
        self.validation_clock()

    def update_value(self) -> None:
        self.value = int(self._spec) * self._factors[self._selected_unit]


class CodeInputCustom(CodeInput):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Cursor must be moved after setting text
        # By scheduling execution will be performed before next frame
        self.bind(
            text=lambda instance, value: Clock.schedule_once(self.on_text_validate)
        )

    def on_text_validate(self, *args: Any) -> None:
        self.cursor = (0, 0)
