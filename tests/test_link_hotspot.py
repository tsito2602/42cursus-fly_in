"""Test the hover area lying along a connection line."""

import math

from typing import Iterator

import flet as ft
import pytest

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.rendering.gui.board import Board
from fly_in.rendering.gui.link_hotspot import LinkHotspot
from fly_in.rendering.gui.theme import LINK_HOVER_THICKNESS
from fly_in.rendering.gui.tooltips import connection_details
from fly_in.rendering.gui.timeline import SimulationTimeline
from fly_in.rendering.gui.view_transform import ViewTransform
from fly_in.routing import RouteSchedule

START = (100.0, 50.0)
END = (400.0, 450.0)


@pytest.fixture(autouse=True)
def detached_update(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Let controls be updated without being attached to a page."""

    monkeypatch.setattr(ft.BaseControl, "update", lambda self: None)

    yield


def make_zone(name: str, x: int, y: int, role: ZoneRole) -> Zone:
    return Zone(
        name=name,
        x=x,
        y=y,
        zone_role=role,
        zone_type=ZoneType.NORMAL,
        color=None,
        capacity=None,
    )


def make_map() -> Map:
    zones = (
        make_zone("start", 0, 0, ZoneRole.START),
        make_zone("middle", 2, 1, ZoneRole.HUB),
        make_zone("goal", 4, 0, ZoneRole.END),
    )

    return Map(
        nb_drones=1,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="middle", capacity=3),
            Connection(zone_a="middle", zone_b="goal"),
        ],
        start="start",
        end="goal",
    )


def make_board() -> Board:
    map = make_map()
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "middle", "goal"))

    return Board(map, SimulationTimeline(map, schedule))


def make_hotspot() -> LinkHotspot:
    return LinkHotspot(
        Connection(zone_a="start", zone_b="middle", capacity=3), START, END
    )


def links_of(board: Board) -> list[LinkHotspot]:
    """Return the hover area of every connection."""

    return [
        control
        for control in board.controls
        if isinstance(control, LinkHotspot)
    ]


def middle(hotspot: LinkHotspot) -> tuple[float, float]:
    """Return the center of a hover area."""

    return (
        float(hotspot.left or 0.0) + float(hotspot.width or 0.0) / 2.0,
        float(hotspot.top or 0.0) + float(hotspot.height or 0.0) / 2.0,
    )


def test_a_hover_area_is_as_long_as_its_line() -> None:
    assert make_hotspot().width == pytest.approx(
        math.hypot(END[0] - START[0], END[1] - START[1])
    )


def test_a_hover_area_is_thick_enough_to_aim_at() -> None:
    hotspot = make_hotspot()

    assert hotspot.height == LINK_HOVER_THICKNESS
    assert LINK_HOVER_THICKNESS > 1.0


def test_a_hover_area_sits_on_the_middle_of_its_line() -> None:
    center = middle(make_hotspot())

    assert center[0] == pytest.approx((START[0] + END[0]) / 2.0)
    assert center[1] == pytest.approx((START[1] + END[1]) / 2.0)


def test_a_hover_area_turns_along_its_line() -> None:
    rotate = make_hotspot().rotate

    assert isinstance(rotate, ft.Rotate)
    assert rotate.angle == pytest.approx(
        math.atan2(END[1] - START[1], END[0] - START[0])
    )


def test_a_flat_line_is_not_turned() -> None:
    hotspot = LinkHotspot(
        Connection(zone_a="start", zone_b="middle"), (10.0, 20.0), (90.0, 20.0)
    )
    rotate = hotspot.rotate

    assert isinstance(rotate, ft.Rotate)
    assert rotate.angle == pytest.approx(0.0)


def test_a_hover_area_shows_the_details_of_its_connection() -> None:
    connection = Connection(zone_a="start", zone_b="middle", capacity=3)

    assert make_hotspot().tooltip == connection_details(connection)


def test_every_connection_carries_a_hover_area() -> None:
    board = make_board()

    assert len(links_of(board)) == len(make_map().connections)


def test_a_hover_area_joins_the_two_zones_it_links() -> None:
    board = make_board()
    map = make_map()
    transform = ViewTransform(
        map.zones.values(), int(board.width or 0), int(board.height or 0)
    )
    start = transform.to_pixel(0, 0)
    end = transform.to_pixel(2, 1)
    center = middle(links_of(board)[0])

    assert center[0] == pytest.approx((start[0] + end[0]) / 2.0)
    assert center[1] == pytest.approx((start[1] + end[1]) / 2.0)


def test_a_hover_area_stays_under_the_zones() -> None:
    kinds = [type(control).__name__ for control in make_board().controls]

    assert kinds.index("LinkHotspot") < kinds.index("ZoneHotspot")


def test_a_resize_moves_every_hover_area() -> None:
    board = make_board()
    before = middle(links_of(board)[0])
    board.resize(600, 400)

    assert middle(links_of(board)[0]) != before
