from fly_in.models import Connection, Map, Zone, ZoneRole, ZoneType
from fly_in.routing import Transit
from fly_in.routing.route_planner import RoutePlanner


def make_hub(
    name: str,
    zone_type: ZoneType = ZoneType.NORMAL,
    capacity: int = 1,
) -> Zone:
    return Zone(
        name=name,
        x=0,
        y=0,
        zone_role=ZoneRole.HUB,
        zone_type=zone_type,
        color=None,
        capacity=capacity,
    )


def make_map(
    hubs: list[Zone],
    connections: list[Connection],
    nb_drones: int = 1,
) -> Map:
    start = Zone(
        name="start",
        x=0,
        y=0,
        zone_role=ZoneRole.START,
        color=None,
        capacity=None,
    )
    goal = Zone(
        name="goal",
        x=0,
        y=0,
        zone_role=ZoneRole.END,
        color=None,
        capacity=None,
    )
    zones = [start, *hubs, goal]

    return Map(
        nb_drones=nb_drones,
        zones={zone.name: zone for zone in zones},
        connections=connections,
        start=start.name,
        end=goal.name,
    )


def test_finds_direct_route_in_either_connection_direction() -> None:
    map = make_map(
        [],
        [Connection(zone_a="goal", zone_b="start")],
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", "goal")


def test_plans_route_for_every_drone() -> None:
    map = make_map(
        [],
        [Connection(zone_a="start", zone_b="goal", capacity=3)],
        nb_drones=3,
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", "goal")
    assert schedule.get_route(2) == ("start", "goal")
    assert schedule.get_route(3) == ("start", "goal")


def test_inserts_transit_before_entering_restricted_zone() -> None:
    restricted = make_hub("restricted", ZoneType.RESTRICTED)
    map = make_map(
        [restricted],
        [
            Connection(zone_a="start", zone_b=restricted.name),
            Connection(zone_a=restricted.name, zone_b="goal"),
        ],
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == (
        "start",
        Transit("start", restricted.name),
        restricted.name,
        "goal",
    )


def test_chooses_route_with_fewer_turns() -> None:
    restricted = make_hub("restricted", ZoneType.RESTRICTED)
    normal = make_hub("normal")
    map = make_map(
        [restricted, normal],
        [
            Connection(zone_a="start", zone_b=restricted.name),
            Connection(zone_a=restricted.name, zone_b="goal"),
            Connection(zone_a="start", zone_b=normal.name),
            Connection(zone_a=normal.name, zone_b="goal"),
        ],
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", normal.name, "goal")


def test_avoids_blocked_zone() -> None:
    blocked = make_hub("blocked", ZoneType.BLOCKED)
    open_hub = make_hub("open")
    map = make_map(
        [blocked, open_hub],
        [
            Connection(zone_a="start", zone_b=blocked.name),
            Connection(zone_a=blocked.name, zone_b="goal"),
            Connection(zone_a="start", zone_b=open_hub.name),
            Connection(zone_a=open_hub.name, zone_b="goal"),
        ],
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", open_hub.name, "goal")


def test_returns_none_when_goal_is_unreachable() -> None:
    map = make_map([], [])

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is None


def test_waits_until_connection_is_available() -> None:
    map = make_map(
        [],
        [Connection(zone_a="start", zone_b="goal")],
        nb_drones=2,
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", "goal")
    assert schedule.get_route(2) == ("start", "start", "goal")


def test_waits_until_destination_zone_has_capacity() -> None:
    hub = make_hub("hub")
    map = make_map(
        [hub],
        [
            Connection(
                zone_a="start",
                zone_b=hub.name,
                capacity=2,
            ),
            Connection(zone_a=hub.name, zone_b="goal"),
        ],
        nb_drones=2,
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == ("start", hub.name, "goal")
    assert schedule.get_route(2) == (
        "start",
        "start",
        hub.name,
        "goal",
    )


def test_restricted_move_waits_for_both_connection_turns() -> None:
    restricted = make_hub("restricted", ZoneType.RESTRICTED)
    map = make_map(
        [restricted],
        [
            Connection(zone_a="start", zone_b=restricted.name),
            Connection(zone_a=restricted.name, zone_b="goal"),
        ],
        nb_drones=2,
    )

    schedule = RoutePlanner(map).plan_routes()

    assert schedule is not None
    assert schedule.get_route(1) == (
        "start",
        Transit("start", restricted.name),
        restricted.name,
        "goal",
    )
    assert schedule.get_route(2) == (
        "start",
        "start",
        "start",
        Transit("start", restricted.name),
        restricted.name,
        "goal",
    )
