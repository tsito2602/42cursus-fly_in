import flet as ft

from .geometry import Point, top_left
from .theme import BACKGROUND, DRONE, DRONE_OUTLINE, outline_width


class CrowdBadge(ft.Container):
    """Show how many drones are stacked on one point."""

    def __init__(self, radius: float, font: float, point: Point) -> None:
        self._count = ft.Text(
            value="",
            size=font,
            color=BACKGROUND,
            weight=ft.FontWeight.BOLD,
        )

        super().__init__(
            width=radius * 2.0,
            height=radius * 2.0,
            bgcolor=DRONE,
            shape=ft.BoxShape.CIRCLE,
            border=ft.Border.all(outline_width(radius), DRONE_OUTLINE),
            alignment=ft.Alignment.CENTER,
            content=self._count,
            visible=False,
        )
        self.left, self.top = top_left(point, radius)

    def set_count(self, count: int) -> None:
        """Show the count, or hide the badge when the crowd is gone."""

        self.visible = count > 0
        self._count.value = str(count)
