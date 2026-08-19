"""Test the mapping from drone locations to pixel points."""

import math
from pathlib import Path

import pytest

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.parsing import MapParser
from fly_in.rendering.gui.board.drone_layout import DroneLayout
from fly_in.rendering.gui.board.transform import Point, ViewTransform
from fly_in.rendering.gui.theme import (
    CROWD_THRESHOLD,
    RING_SLOTS,
    drone_radius,
)
from fly_in.rendering.gui.timeline import SimulationTimeline
from fly_in.routing import RoutePlanner, Route, RouteSchedule, Transit

WIDTH = 1200
HEIGHT = 700

MAP_FILES = sorted(Path("maps").glob("*/*.txt"))


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


def make_map(nb_drones: int) -> Map:
    zones = (
        make_zone("start", 0, 0, ZoneRole.START),
        make_zone("middle", 2, 0, ZoneRole.HUB),
        make_zone("goal", 4, 0, ZoneRole.END),
    )

    return Map(
        nb_drones=nb_drones,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="middle"),
            Connection(zone_a="middle", zone_b="goal"),
        ],
        start="start",
        end="goal",
    )


def make_layout(routes: dict[int, Route]) -> DroneLayout:
    map = make_map(len(routes))
    schedule = RouteSchedule()

    for drone_id, route in routes.items():
        schedule.add_route(drone_id, route)

    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    return DroneLayout(map, SimulationTimeline(map, schedule), transform)


def make_crowd(nb_drones: int) -> DroneLayout:
    """Return a layout whose drones all sit on start at turn 0."""

    return make_layout(
        {
            drone_id: ("start", "middle", "goal")
            for drone_id in range(1, nb_drones + 1)
        }
    )


def spacing_of(nb_drones: int) -> float:
    map = make_map(nb_drones)
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    return drone_radius(transform.scale) * 2.4


def center_of(zone: str, nb_drones: int) -> Point:
    map = make_map(nb_drones)
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    return transform.to_pixel(map.zones[zone].x, map.zones[zone].y)


def distance(first: Point, second: Point) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def midpoint(first: Point, second: Point) -> Point:
    return ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)


def average(points: list[Point]) -> Point:
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def test_a_lone_drone_sits_exactly_on_the_zone_center() -> None:
    layout = make_crowd(1)

    assert layout.points_at(0)[1] == center_of("start", 1)


def test_two_drones_sit_on_opposite_sides_of_the_center() -> None:
    layout = make_crowd(2)
    center = center_of("start", 2)
    first, second = layout.points_at(0)[1], layout.points_at(0)[2]

    assert midpoint(first, second) == pytest.approx(center)
    assert distance(first, second) == pytest.approx(spacing_of(2) * 2.0)


def test_two_drones_sit_side_by_side() -> None:
    layout = make_crowd(2)
    _, center_y = center_of("start", 2)
    first, second = layout.points_at(0)[1], layout.points_at(0)[2]

    assert first[1] == pytest.approx(center_y)
    assert second[1] == pytest.approx(center_y)


@pytest.mark.parametrize("nb_drones", range(2, RING_SLOTS + 1))
def test_a_group_leaves_the_center_empty(nb_drones: int) -> None:
    layout = make_crowd(nb_drones)
    center = center_of("start", nb_drones)

    for point in layout.points_at(0).values():
        assert distance(point, center) == pytest.approx(
            spacing_of(nb_drones)
        )


@pytest.mark.parametrize("nb_drones", range(2, RING_SLOTS + 1))
def test_a_group_stays_centered_on_its_zone(nb_drones: int) -> None:
    layout = make_crowd(nb_drones)
    points = list(layout.points_at(0).values())

    assert average(points) == pytest.approx(
        center_of("start", nb_drones)
    )


@pytest.mark.parametrize("nb_drones", range(3, RING_SLOTS + 1))
def test_a_group_spaces_its_drones_evenly(nb_drones: int) -> None:
    layout = make_crowd(nb_drones)
    points = layout.points_at(0)
    gaps = [
        distance(points[drone_id], points[drone_id % nb_drones + 1])
        for drone_id in range(1, nb_drones + 1)
    ]

    assert gaps == pytest.approx([gaps[0]] * nb_drones)


def test_the_first_drone_of_a_group_sits_above_the_center() -> None:
    layout = make_crowd(4)
    center_x, center_y = center_of("start", 4)

    x, y = layout.points_at(0)[1]

    assert x == pytest.approx(center_x)
    assert y == pytest.approx(center_y - spacing_of(4))


def test_the_polygon_seats_every_drone_below_the_crowd_size() -> None:
    assert CROWD_THRESHOLD == RING_SLOTS + 1


def test_a_crowd_stacks_every_drone_on_the_center() -> None:
    layout = make_crowd(CROWD_THRESHOLD)
    center = center_of("start", CROWD_THRESHOLD)

    assert set(layout.points_at(0).values()) == {center}


def test_a_crowd_is_counted() -> None:
    layout = make_crowd(20)

    assert layout.crowds_at(0) == {center_of("start", 20): 20}


def test_a_full_polygon_is_not_a_crowd() -> None:
    layout = make_crowd(CROWD_THRESHOLD - 1)

    assert layout.crowds_at(0) == {}


def test_a_crowd_breaks_up_as_drones_leave() -> None:
    routes: dict[int, Route] = {1: ("start", "middle", "goal")}

    for drone_id in range(2, CROWD_THRESHOLD + 1):
        routes[drone_id] = ("start", "start", "middle", "goal")

    layout = make_layout(routes)

    assert layout.crowds_at(0) == {
        center_of("start", CROWD_THRESHOLD): CROWD_THRESHOLD
    }
    assert layout.crowds_at(1) == {}


def test_crowd_points_collects_every_crowded_location() -> None:
    layout = make_crowd(20)

    assert set(layout.crowd_points()) == {
        center_of("start", 20),
        center_of("middle", 20),
        center_of("goal", 20),
    }


def test_crowd_points_is_empty_without_a_crowd() -> None:
    layout = make_crowd(2)

    assert layout.crowd_points() == ()


def test_crowds_at_clamps_a_negative_turn() -> None:
    layout = make_crowd(20)

    assert layout.crowds_at(-1) == layout.crowds_at(0)


def test_crowds_at_clamps_a_turn_past_the_end() -> None:
    layout = make_crowd(20)

    assert layout.crowds_at(99) == layout.crowds_at(2)


@pytest.mark.parametrize("nb_drones", [2, 4, RING_SLOTS])
def test_neighbours_never_overlap(nb_drones: int) -> None:
    layout = make_crowd(nb_drones)
    points = list(layout.points_at(0).values())
    diameter = spacing_of(nb_drones) / 1.2

    for index, first in enumerate(points):
        for second in points[index + 1:]:
            assert distance(first, second) >= diameter


def test_no_two_drones_share_a_point() -> None:
    layout = make_crowd(RING_SLOTS)
    points = layout.points_at(0)

    assert len(set(points.values())) == RING_SLOTS


def test_a_transit_drone_sits_on_the_connection_midpoint() -> None:
    layout = make_layout(
        {1: ("start", Transit("start", "middle"), "middle")}
    )
    start_x, start_y = center_of("start", 1)
    middle_x, middle_y = center_of("middle", 1)

    assert layout.points_at(1)[1] == pytest.approx(
        ((start_x + middle_x) / 2.0, (start_y + middle_y) / 2.0)
    )


def test_drones_regroup_when_a_neighbour_leaves() -> None:
    layout = make_layout(
        {
            1: ("start", "middle", "goal"),
            2: ("start", "start", "middle"),
        }
    )

    assert layout.points_at(0)[2] != center_of("start", 2)
    assert layout.points_at(1)[2] == center_of("start", 2)


def test_points_at_clamps_a_negative_turn() -> None:
    layout = make_crowd(2)

    assert layout.points_at(-1) == layout.points_at(0)


def test_points_at_clamps_a_turn_past_the_end() -> None:
    layout = make_crowd(2)

    assert layout.points_at(99) == layout.points_at(2)


def test_points_at_returns_the_cached_dictionary() -> None:
    layout = make_crowd(2)

    assert layout.points_at(1) is layout.points_at(1)


def test_the_layout_is_deterministic() -> None:
    assert make_crowd(9).points_at(0) == make_crowd(9).points_at(0)


@pytest.mark.parametrize("map_file", MAP_FILES, ids=lambda p: p.stem)
def test_every_drone_has_a_point_on_every_turn(map_file: Path) -> None:
    map = MapParser(str(map_file)).load()
    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None

    timeline = SimulationTimeline(map, schedule)
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)
    layout = DroneLayout(map, timeline, transform)

    for turn in range(timeline.last_turn + 1):
        assert len(layout.points_at(turn)) == map.nb_drones


@pytest.mark.parametrize("map_file", MAP_FILES, ids=lambda p: p.stem)
def test_no_point_leaves_the_canvas(map_file: Path) -> None:
    map = MapParser(str(map_file)).load()
    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None

    timeline = SimulationTimeline(map, schedule)
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)
    layout = DroneLayout(map, timeline, transform)
    radius = drone_radius(transform.scale)

    for turn in range(timeline.last_turn + 1):
        for x, y in layout.points_at(turn).values():
            assert radius <= x <= WIDTH - radius
            assert radius <= y <= HEIGHT - radius
