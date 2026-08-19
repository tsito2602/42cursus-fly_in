import flet as ft

from ..theme import (
    DRONE,
    DRONE_OUTLINE,
    TURN_SECONDS,
    animation_ms,
    outline_width,
)
from .transform import Point, top_left


class DroneMarker(ft.Container):
    """Show one drone as a dot that animates between turns."""

    def __init__(self, drone_id: int, radius: float, point: Point) -> None:
        self._radius = radius

        super().__init__(
            width=radius * 2.0,
            height=radius * 2.0,
            bgcolor=DRONE,
            shape=ft.BoxShape.CIRCLE,
            border=ft.Border.all(outline_width(radius), DRONE_OUTLINE),
            tooltip=f"D{drone_id}",
        )
        self.set_duration(animation_ms(TURN_SECONDS))
        self.move_to(point)

    def move_to(self, point: Point) -> None:
        """Place the marker so that its center sits on the point."""

        self.left, self.top = top_left(point, self._radius)

    def set_duration(self, milliseconds: int) -> None:
        """Match the animation length to the playback speed."""

        self.animate_position = ft.Animation(
            duration=milliseconds, curve=ft.AnimationCurve.EASE_IN_OUT
        )
