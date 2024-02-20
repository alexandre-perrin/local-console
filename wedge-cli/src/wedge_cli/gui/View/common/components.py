import enum
from math import fabs

from kivy.core.window import Window
from kivy.graphics import Color
from kivy.graphics import Line
from kivy.input import MotionEvent
from kivy.properties import ObjectProperty
from kivymd.uix.fitimage import FitImage


class ImageWithROI(FitImage):
    ROI = ObjectProperty()

    class DrawState(enum.Enum):
        Viewing = enum.auto()
        PickingStartPoint = enum.auto()
        PickingEndPoint = enum.auto()

    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)
        self.user_state = self.DrawState.Viewing
        self.roi_start: tuple[float, float] = (0, 0)
        self.rect_start: tuple[int, int] = (0, 0)
        self.rect_end: tuple[int, int] = (0, 0)
        self.rect_size: tuple[int, int] = (0, 0)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def activate_select_mode(self) -> None:
        self.user_state = self.DrawState.PickingStartPoint
        with self.canvas:
            self.canvas.clear()
        # Change mouse cursor to crosshair
        Window.cursor = "crosshair"

    def on_touch_down(self, touch: MotionEvent) -> bool:
        if self.user_state == self.DrawState.PickingStartPoint and self.collide_point(
            *touch.pos
        ):
            self.rect_start = touch.pos
            self.roi_start = touch.spos
            self.user_state = self.DrawState.PickingEndPoint
            return True  # to consume the event and not propagate it further

        elif self.user_state == self.DrawState.PickingEndPoint and self.collide_point(
            *touch.pos
        ):
            self.rect_end = touch.pos
            self.user_state = self.DrawState.Viewing
            Window.cursor = "default"  # Reset cursor
            roi_min = (
                min(self.roi_start[0], touch.sx),
                min(self.roi_start[1], touch.sy),
            )
            self.rect_size = (
                int(fabs(self.roi_start[0] - touch.sx)),
                int(fabs(self.roi_start[1] - touch.sy)),
            )
            self.roi_start = roi_min
            self.ROI = (self.roi_start, self.rect_size)
            self.draw_rectangle()
            return True  # to consume the event and not propagate it further

        return bool(super().on_touch_down(touch))

    def on_mouse_pos(self, _window: Window, pos: tuple[int, int]) -> None:
        if self.user_state == self.DrawState.PickingEndPoint and self.collide_point(
            *pos
        ):
            self.rect_end = pos
            self.draw_rectangle()

    def draw_rectangle(self) -> None:
        rect_size = (
            int(fabs(self.rect_end[0] - self.rect_start[0])),
            int(fabs(self.rect_end[1] - self.rect_start[1])),
        )
        r_start = (
            min(self.rect_end[0], self.rect_start[0]),
            min(self.rect_end[1], self.rect_start[1]),
        )
        with self.canvas:
            self.canvas.clear()
            Color(1, 0, 0, 1)
            Line(rectangle=[*r_start, rect_size[0], rect_size[1]], width=1.5)
