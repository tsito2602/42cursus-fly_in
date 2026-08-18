import flet as ft

from fly_in.models import Zone

from .theme import zone_details
from .drone_layout import Point, top_left


class ZoneHotspot(ft.Container):
    """Show the details of one zone while the pointer rests on it."""

    def __init__(self, zone: Zone, radius: float, point: Point) -> None:
        super().__init__(
            width=radius * 2.0,
            height=radius * 2.0,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=ft.Colors.TRANSPARENT,
            tooltip=zone_details(zone),
        )
        self.left, self.top = top_left(point, radius)
