"""Test the gradient covering a rainbow zone."""

import flet as ft

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.rendering.gui.board import Board
from fly_in.rendering.gui.rainbow_zone import RainbowZone
from fly_in.rendering.gui.theme import (
    OUTLINE_WIDTH,
    RAINBOW,
    RAINBOW_COLORS,
    drawn_radius,
)
from fly_in.rendering.gui.timeline import SimulationTimeline
from fly_in.rendering.gui.transform import ViewTransform
from fly_in.routing import RouteSchedule


def make_zone(name: str, x: int, role: ZoneRole, color: str | None) -> Zone:
    return Zone(
        name=name,
        x=x,
        y=0,
        zone_role=role,
        zone_type=ZoneType.NORMAL,
        color=color,
        capacity=None,
    )


def make_map() -> Map:
    zones = (
        make_zone("start", 0, ZoneRole.START, None),
        make_zone("middle", 2, ZoneRole.HUB, "red"),
        make_zone("goal", 4, ZoneRole.END, RAINBOW),
    )

    return Map(
        nb_drones=1,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="middle"),
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


def rainbows_of(board: Board) -> list[RainbowZone]:
    """Return the gradient of every rainbow zone."""

    return [
        control
        for control in board.controls
        if isinstance(control, RainbowZone)
    ]


def test_the_rainbow_closes_on_itself() -> None:
    assert RAINBOW_COLORS[0] == RAINBOW_COLORS[-1]
    assert len(set(RAINBOW_COLORS)) == len(RAINBOW_COLORS) - 1


def test_a_rainbow_zone_carries_a_sweeping_gradient() -> None:
    zone = make_zone("goal", 4, ZoneRole.END, RAINBOW)
    gradient = RainbowZone(zone, 20.0, (100.0, 50.0)).gradient

    assert isinstance(gradient, ft.SweepGradient)
    assert gradient.colors == list(RAINBOW_COLORS)


def test_a_rainbow_stays_round() -> None:
    zone = make_zone("goal", 4, ZoneRole.END, RAINBOW)
    circle = RainbowZone(zone, 20.0, (100.0, 50.0))

    assert circle.shape is ft.BoxShape.CIRCLE
    assert circle.width == circle.height


def test_a_rainbow_leaves_the_zone_outline_visible() -> None:
    zone = make_zone("goal", 4, ZoneRole.END, RAINBOW)
    circle = RainbowZone(zone, 20.0, (100.0, 50.0))

    assert circle.width == (20.0 - OUTLINE_WIDTH / 2.0) * 2.0


def test_a_rainbow_sits_on_its_zone() -> None:
    zone = make_zone("goal", 4, ZoneRole.END, RAINBOW)
    circle = RainbowZone(zone, 20.0, (100.0, 50.0))

    left = float(circle.left or 0.0)
    top = float(circle.top or 0.0)

    assert left + float(circle.width or 0.0) / 2.0 == 100.0
    assert top + float(circle.height or 0.0) / 2.0 == 50.0


def test_only_a_rainbow_zone_gets_a_gradient() -> None:
    board = make_board()

    assert len(rainbows_of(board)) == 1


def test_the_gradient_covers_the_drawn_zone() -> None:
    board = make_board()
    map = make_map()
    transform = ViewTransform(
        map.zones.values(), int(board.width or 0), int(board.height or 0)
    )
    goal = map.zones["goal"]
    circle = rainbows_of(board)[0]

    assert circle.width == (
        drawn_radius(goal, transform.scale) - OUTLINE_WIDTH / 2.0
    ) * 2.0


def test_the_gradient_stays_under_the_drones() -> None:
    board = make_board()
    kinds = [type(control).__name__ for control in board.controls]

    assert kinds.index("RainbowZone") < kinds.index("DroneMarker")
