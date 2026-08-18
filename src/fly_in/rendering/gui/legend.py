import flet as ft
import flet.canvas as cv

from fly_in.models import ZoneType

from .theme import (
    DASH_PATTERN,
    LABEL,
    OUTLINE_WIDTH,
    TYPE_COLORS,
    outline_dashed,
)

FONT_SIZE = 11
SWATCH_WIDTH = 22
SWATCH_HEIGHT = 10

ZONE_TYPES = (
    ZoneType.NORMAL,
    ZoneType.PRIORITY,
    ZoneType.RESTRICTED,
    ZoneType.BLOCKED,
)


class Legend(ft.Row):
    """Show which zone type each outline color stands for."""

    def __init__(self) -> None:
        super().__init__(
            controls=[self._entry(zone_type) for zone_type in ZONE_TYPES],
            spacing=14,
        )

    @classmethod
    def _entry(cls, zone_type: ZoneType) -> ft.Row:
        """Return one outline sample with its caption."""

        return ft.Row(
            controls=[
                cls._swatch(zone_type),
                ft.Text(
                    zone_type.value.capitalize(),
                    size=FONT_SIZE,
                    color=LABEL,
                ),
            ],
            spacing=4,
        )

    @staticmethod
    def _swatch(zone_type: ZoneType) -> cv.Canvas:
        """Return a short line drawn like the outline of a zone."""

        middle = SWATCH_HEIGHT / 2.0

        return cv.Canvas(
            width=SWATCH_WIDTH,
            height=SWATCH_HEIGHT,
            shapes=[
                cv.Line(
                    x1=0.0,
                    y1=middle,
                    x2=float(SWATCH_WIDTH),
                    y2=middle,
                    paint=ft.Paint(
                        color=TYPE_COLORS[zone_type],
                        stroke_width=OUTLINE_WIDTH,
                        stroke_dash_pattern=(
                            list(DASH_PATTERN)
                            if outline_dashed(zone_type)
                            else None
                        ),
                    ),
                )
            ],
        )
