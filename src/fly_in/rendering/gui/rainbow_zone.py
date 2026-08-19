import flet as ft

from fly_in.models import Zone

from .geometry import Point, top_left
from .theme import OUTLINE_WIDTH, RAINBOW_COLORS


class RainbowZone(ft.Container):
    """Fill one zone with colors turning around its center."""

    def __init__(self, zone: Zone, radius: float, point: Point) -> None:
        inner = radius - OUTLINE_WIDTH / 2.0

        super().__init__(
            width=inner * 2.0,
            height=inner * 2.0,
            shape=ft.BoxShape.CIRCLE,
            gradient=ft.SweepGradient(colors=list(RAINBOW_COLORS)),
            tooltip=zone.name,
        )
        self.left, self.top = top_left(point, inner)
