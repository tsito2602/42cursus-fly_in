"""Show a panel of details while the pointer rests on a shape.

The canvas draws the map but cannot react to the mouse, so each tooltip
is an invisible container laid over the shape it describes.
"""

import math

import flet as ft

from fly_in.models import Connection, Zone, ZoneRole

from .theme import CONNECTION_TOOLTIP_THICKNESS
from .transform import Point, top_left


class ZoneTooltip(ft.Container):
    """Cover one zone with the circle listening for the pointer."""

    def __init__(self, zone: Zone, radius: float, point: Point) -> None:
        super().__init__(
            width=radius * 2.0,
            height=radius * 2.0,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=ft.Colors.TRANSPARENT,
            tooltip=zone_details(zone),
        )
        self.left, self.top = top_left(point, radius)


class ConnectionTooltip(ft.Container):
    """Cover one connection with the bar listening for the pointer."""

    def __init__(
        self, connection: Connection, start: Point, end: Point
    ) -> None:
        x1, y1 = start
        x2, y2 = end
        length = math.hypot(x2 - x1, y2 - y1)

        super().__init__(
            width=length,
            height=CONNECTION_TOOLTIP_THICKNESS,
            bgcolor=ft.Colors.TRANSPARENT,
            rotate=ft.Rotate(math.atan2(y2 - y1, x2 - x1)),
            tooltip=connection_details(connection),
        )
        self.left = (x1 + x2) / 2.0 - length / 2.0
        self.top = (y1 + y2) / 2.0 - CONNECTION_TOOLTIP_THICKNESS / 2.0


def zone_details(zone: Zone) -> str:
    """Return the lines describing a zone on its tooltip."""

    capacity = "unlimited" if zone.capacity is None else zone.capacity
    lines = [
        f"name: {zone.name}",
        f"type: {zone.zone_type.value}",
        f"capacity: {capacity}",
        f"position: ({zone.x}, {zone.y})",
    ]

    if zone.zone_role is not ZoneRole.HUB:
        lines.insert(1, f"role: {zone.zone_role.value}")

    if zone.color is not None:
        lines.append(f"color: {zone.color}")

    return "\n".join(lines)


def connection_details(connection: Connection) -> str:
    """Return the lines describing a connection on its tooltip."""

    return "\n".join(
        [
            f"zones: {connection.zone_a} - {connection.zone_b}",
            f"capacity: {connection.capacity}",
        ]
    )
