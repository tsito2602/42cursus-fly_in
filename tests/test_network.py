"""Test the static shapes drawn for the map."""

import flet as ft
import flet.canvas as cv
import pytest

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.rendering.gui.network import NetworkCanvas
from fly_in.rendering.gui.theme import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    RAINBOW_COLORS,
    ROLE_COLORS,
    zone_fill,
)
from fly_in.rendering.gui.view_transform import ViewTransform

WIDTH = CANVAS_WIDTH
HEIGHT = CANVAS_HEIGHT


def make_zone(
    name: str,
    x: int,
    y: int,
    role: ZoneRole,
    zone_type: ZoneType = ZoneType.NORMAL,
    capacity: int | None = 1,
    color: str | None = None,
) -> Zone:
    return Zone(
        name=name,
        x=x,
        y=y,
        zone_role=role,
        zone_type=zone_type,
        color=color,
        capacity=capacity,
    )


def make_map(middle: Zone) -> Map:
    zones = (
        make_zone("start", 0, 0, ZoneRole.START, capacity=None),
        middle,
        make_zone("goal", 4, 0, ZoneRole.END, capacity=None),
    )

    return Map(
        nb_drones=2,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="middle"),
            Connection(zone_a="middle", zone_b="goal", capacity=3),
        ],
        start="start",
        end="goal",
    )


def make_canvas(middle: Zone) -> NetworkCanvas:
    map = make_map(middle)
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    return NetworkCanvas(map, transform, WIDTH, HEIGHT)


def texts_of(canvas: NetworkCanvas) -> list[str]:
    """Return every string drawn on the canvas."""

    return [
        str(shape.value)
        for shape in canvas.shapes
        if isinstance(shape, cv.Text)
    ]


def test_the_canvas_takes_the_given_size() -> None:
    canvas = make_canvas(make_zone("middle", 2, 0, ZoneRole.HUB))

    assert canvas.width == WIDTH
    assert canvas.height == HEIGHT


def test_the_start_and_the_goal_are_labelled() -> None:
    canvas = make_canvas(make_zone("middle", 2, 0, ZoneRole.HUB))

    assert "START" in texts_of(canvas)
    assert "GOAL" in texts_of(canvas)


def test_a_hub_carries_no_role_badge() -> None:
    canvas = make_canvas(make_zone("middle", 2, 0, ZoneRole.HUB))
    badges = [
        shape
        for shape in canvas.shapes
        if isinstance(shape, cv.Text)
        and shape.style is not None
        and shape.style.color in set(ROLE_COLORS.values())
    ]

    assert len(badges) == 2
    assert texts_of(canvas) == ["START", "GOAL"]


def test_no_zone_name_is_drawn_on_the_canvas() -> None:
    canvas = make_canvas(
        make_zone("middle", 2, 0, ZoneRole.HUB, capacity=4)
    )

    for text in texts_of(canvas):
        assert "middle" not in text
        assert "4" not in text


def test_a_blocked_zone_is_crossed_out() -> None:
    plain = make_canvas(make_zone("middle", 2, 0, ZoneRole.HUB))
    blocked = make_canvas(
        make_zone("middle", 2, 0, ZoneRole.HUB, ZoneType.BLOCKED)
    )

    def lines(canvas: NetworkCanvas) -> int:
        return sum(
            1 for shape in canvas.shapes if isinstance(shape, cv.Line)
        )

    assert lines(blocked) == lines(plain) + 2


@pytest.mark.parametrize("zone_type", list(ZoneType))
def test_every_zone_type_can_be_drawn(zone_type: ZoneType) -> None:
    canvas = make_canvas(
        make_zone("middle", 2, 0, ZoneRole.HUB, zone_type)
    )

    assert canvas.shapes


def test_a_wider_link_is_drawn_thicker() -> None:
    canvas = make_canvas(make_zone("middle", 2, 0, ZoneRole.HUB))
    widths = sorted(
        float(shape.paint.stroke_width or 0.0)
        for shape in canvas.shapes
        if isinstance(shape, cv.Line) and shape.paint is not None
    )

    assert widths == [5.0, 13.0]


def fills_of(canvas: NetworkCanvas) -> list[ft.Paint]:
    """Return the paint of every filled zone circle."""

    return [
        shape.paint
        for shape in canvas.shapes
        if isinstance(shape, cv.Circle)
        and shape.paint is not None
        and shape.paint.style is not ft.PaintingStyle.STROKE
    ]


def test_a_plain_zone_is_filled_with_one_color() -> None:
    zone = make_zone("middle", 2, 0, ZoneRole.HUB, color="red")
    middle = fills_of(make_canvas(zone))[1]

    assert middle.gradient is None
    assert middle.color == zone_fill(zone)


def test_the_rainbow_closes_on_itself() -> None:
    assert RAINBOW_COLORS[0] == RAINBOW_COLORS[-1]
    assert len(set(RAINBOW_COLORS)) == len(RAINBOW_COLORS) - 1
