import flet as ft
import flet.canvas as cv

from fly_in.models import Map, Connection, Zone, ZoneRole, ZoneType
from .theme import (
    DASH_PATTERN,
    LINE,
    OUTLINE_WIDTH,
    ROLE_COLORS,
    ROLE_LABELS,
    TYPE_COLORS,
    drawn_radius,
    label_size,
    outline_dashed,
    zone_fill,
)
from .view_transform import ViewTransform


class NetworkCanvas(cv.Canvas):
    """Draw the static part of the map: connections, zones, labels."""

    def __init__(
        self,
        map: Map,
        transform: ViewTransform,
        width: int,
        height: int,
    ) -> None:
        self._map = map
        self._transform = transform
        self._font = label_size(transform.scale)

        shapes: list[cv.Shape] = []

        for connection in map.connections:
            shapes.extend(self._connection_shapes(connection))

        for zone in map.zones.values():
            shapes.extend(self._zone_shapes(zone))

        super().__init__(width=width, height=height, shapes=shapes)

    def _connection_shapes(self, connection: Connection) -> list[cv.Shape]:
        """Return the shapes drawing one connection."""

        zone_a = self._map.zones[connection.zone_a]
        zone_b = self._map.zones[connection.zone_b]

        x1, y1 = self._transform.to_pixel(zone_a.x, zone_a.y)
        x2, y2 = self._transform.to_pixel(zone_b.x, zone_b.y)

        return [
            cv.Line(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                paint=ft.Paint(
                    color=LINE,
                    stroke_width=1.0 + connection.capacity * 4.0,
                    stroke_cap=ft.StrokeCap.ROUND,
                ),
            )
        ]

    def _zone_shapes(self, zone: Zone) -> list[cv.Shape]:
        """Return the shapes drawing one zone."""

        x, y = self._transform.to_pixel(zone.x, zone.y)
        radius = drawn_radius(zone, self._transform.scale)

        shapes: list[cv.Shape] = [
            cv.Circle(
                x=x,
                y=y,
                radius=radius,
                paint=ft.Paint(color=zone_fill(zone)),
            ),
            cv.Circle(
                x=x,
                y=y,
                radius=radius,
                paint=self._outline_paint(zone),
            ),
        ]

        if zone.zone_role is not ZoneRole.HUB:
            shapes.append(self._role_shape(zone, x, y, radius))

        if zone.zone_type is ZoneType.BLOCKED:
            shapes.extend(self._cross_shapes(x, y, radius))

        return shapes

    def _role_shape(
        self, zone: Zone, x: float, y: float, radius: float
    ) -> cv.Shape:
        """Return the START or GOAL badge sitting above a zone."""

        return cv.Text(
            x=x,
            y=y - radius - 4,
            value=ROLE_LABELS[zone.zone_role],
            style=ft.TextStyle(
                size=self._font,
                color=ROLE_COLORS[zone.zone_role],
                weight=ft.FontWeight.BOLD,
            ),
            alignment=ft.Alignment.BOTTOM_CENTER,
        )

    @staticmethod
    def _cross_shapes(x: float, y: float, radius: float) -> list[cv.Shape]:
        """Return the two lines crossing out a blocked zone."""

        arm = radius * 0.7
        paint = ft.Paint(
            color=TYPE_COLORS[ZoneType.BLOCKED],
            stroke_width=2.0,
            stroke_cap=ft.StrokeCap.ROUND,
        )

        return [
            cv.Line(
                x1=x - arm, y1=y - arm, x2=x + arm, y2=y + arm, paint=paint
            ),
            cv.Line(
                x1=x - arm, y1=y + arm, x2=x + arm, y2=y - arm, paint=paint
            ),
        ]

    @staticmethod
    def _outline_paint(zone: Zone) -> ft.Paint:
        """Return the outline paint carrying the zone type."""

        return ft.Paint(
            color=TYPE_COLORS[zone.zone_type],
            stroke_width=OUTLINE_WIDTH,
            style=ft.PaintingStyle.STROKE,
            stroke_dash_pattern=(
                list(DASH_PATTERN)
                if outline_dashed(zone.zone_type)
                else None
            ),
        )
