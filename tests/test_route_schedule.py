import pytest

from fly_in.models.connection import Connection
from fly_in.models.zone import Zone, ZoneRole
from fly_in.routing import Route, RouteSchedule, Transit


def make_zone(name: str, capacity: int | None = 1) -> Zone:
    return Zone(
        name=name,
        x=0,
        y=0,
        zone_role=ZoneRole.HUB,
        color=None,
        capacity=capacity,
    )


def test_add_route_reserves_each_zone_at_its_turn() -> None:
    schedule = RouteSchedule()
    start = make_zone("start")
    goal = make_zone("goal")

    schedule.add_route(1, (start.name, goal.name))

    assert not schedule.can_enter_zone(0, start)
    assert schedule.can_enter_zone(1, start)
    assert schedule.can_enter_zone(0, goal)
    assert not schedule.can_enter_zone(1, goal)


def test_get_route_returns_registered_route() -> None:
    schedule = RouteSchedule()
    route: Route = ("start", "goal")

    schedule.add_route(1, route)

    assert schedule.get_route(1) == route


def test_get_route_rejects_unknown_drone_id() -> None:
    schedule = RouteSchedule()

    with pytest.raises(ValueError):
        schedule.get_route(1)


def test_wait_reserves_zone_without_reserving_connection() -> None:
    schedule = RouteSchedule()
    hub = make_zone("hub")
    goal = make_zone("goal")
    connection = Connection(zone_a=hub.name, zone_b=goal.name)

    schedule.add_route(1, (hub.name, hub.name, goal.name))

    assert not schedule.can_enter_zone(0, hub)
    assert not schedule.can_enter_zone(1, hub)
    assert schedule.can_use_connection(0, connection)
    assert not schedule.can_use_connection(1, connection)
    assert not schedule.can_enter_zone(2, goal)


def test_move_reserves_connection_in_both_directions() -> None:
    schedule = RouteSchedule()
    forward = Connection(zone_a="a", zone_b="b")
    reverse = Connection(zone_a="b", zone_b="a")

    schedule.add_route(1, ("a", "b"))

    assert not schedule.can_use_connection(0, forward)
    assert not schedule.can_use_connection(0, reverse)
    assert schedule.can_use_connection(1, forward)


def test_reservations_respect_zone_and_connection_capacity() -> None:
    schedule = RouteSchedule()
    start = make_zone("start", capacity=2)
    goal = make_zone("goal", capacity=2)
    connection = Connection(
        zone_a=start.name,
        zone_b=goal.name,
        capacity=2,
    )

    schedule.add_route(1, (start.name, goal.name))

    assert schedule.can_enter_zone(0, start)
    assert schedule.can_enter_zone(1, goal)
    assert schedule.can_use_connection(0, connection)

    schedule.add_route(2, (start.name, goal.name))

    assert not schedule.can_enter_zone(0, start)
    assert not schedule.can_enter_zone(1, goal)
    assert not schedule.can_use_connection(0, connection)


def test_transit_reserves_connection_for_two_turns() -> None:
    schedule = RouteSchedule()
    origin = make_zone("origin")
    destination = make_zone("destination")
    connection = Connection(
        zone_a=origin.name,
        zone_b=destination.name,
    )

    schedule.add_route(
        1,
        (
            origin.name,
            Transit(origin.name, destination.name),
            destination.name,
        ),
    )

    assert not schedule.can_enter_zone(0, origin)
    assert schedule.can_enter_zone(1, origin)
    assert schedule.can_enter_zone(1, destination)
    assert not schedule.can_enter_zone(2, destination)
    assert not schedule.can_use_connection(0, connection)
    assert not schedule.can_use_connection(1, connection)
    assert schedule.can_use_connection(2, connection)


def test_unlimited_zone_remains_available() -> None:
    schedule = RouteSchedule()
    start = make_zone("start", capacity=None)

    schedule.add_route(1, (start.name, start.name))

    assert schedule.can_enter_zone(0, start)
    assert schedule.can_enter_zone(1, start)


def test_rejects_duplicate_drone_id_without_reserving_new_route() -> None:
    schedule = RouteSchedule()
    first = make_zone("first")
    second = make_zone("second")
    schedule.add_route(1, (first.name,))

    with pytest.raises(ValueError, match="Drone 1 already has a route"):
        schedule.add_route(1, (second.name,))

    assert not schedule.can_enter_zone(0, first)
    assert schedule.can_enter_zone(0, second)
