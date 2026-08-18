import math

import flet as ft

from fly_in.models import Connection

from .theme import LINK_HOVER_THICKNESS, connection_details
from .drone_layout import Point


class LinkHotspot(ft.Container):
    """Show the details of one connection while the pointer rests on it."""

    def __init__(
        self, connection: Connection, start: Point, end: Point
    ) -> None:
        x1, y1 = start
        x2, y2 = end
        length = math.hypot(x2 - x1, y2 - y1)

        super().__init__(
            width=length,
            height=LINK_HOVER_THICKNESS,
            bgcolor=ft.Colors.TRANSPARENT,
            rotate=ft.Rotate(math.atan2(y2 - y1, x2 - x1)),
            tooltip=connection_details(connection),
        )
        self.left = (x1 + x2) / 2.0 - length / 2.0
        self.top = (y1 + y2) / 2.0 - LINK_HOVER_THICKNESS / 2.0
