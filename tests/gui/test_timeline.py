from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.rendering.gui.timeline import SimulationTimeline, TurnState
from fly_in.routing import RouteSchedule, Transit


def make_zone(
    name: str,
    role: ZoneRole = ZoneRole.HUB,
    zone_type: ZoneType = ZoneType.NORMAL,
    capacity: int | None = 1,
) -> Zone:
    return Zone(
        name=name,
        x=0,
        y=0,
        zone_role=role,
        zone_type=zone_type,
        color=None,
        capacity=capacity,
    )


def make_map() -> Map:
    zones = (
        make_zone("start", role=ZoneRole.START, capacity=None),
        make_zone("fast"),
        make_zone("slow", zone_type=ZoneType.RESTRICTED),
        make_zone("goal", role=ZoneRole.END, capacity=None),
    )

    return Map(
        nb_drones=3,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="fast"),
            Connection(zone_a="start", zone_b="slow"),
            Connection(zone_a="fast", zone_b="goal"),
            Connection(zone_a="slow", zone_b="goal"),
        ],
        start="start",
        end="goal",
    )


def make_timeline() -> SimulationTimeline:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "fast", "goal"))
    schedule.add_route(
        2, ("start", Transit("start", "slow"), "slow", "goal")
    )
    schedule.add_route(3, ("start", "start", "fast", "goal"))

    return SimulationTimeline(make_map(), schedule)


def test_last_turn_matches_the_longest_route() -> None:
    assert make_timeline().last_turn == 3


def test_every_drone_starts_in_the_start_zone() -> None:
    state = make_timeline().state_at(0)

    assert state.turn == 0
    assert state.zone_occupancy == {"start": (1, 2, 3)}
    assert state.connection_occupancy == {}
    assert state.delivered == 0
    assert state.in_flight == 0


def test_transit_is_reported_as_connection_occupancy() -> None:
    state = make_timeline().state_at(1)

    assert state.zone_occupancy == {"fast": (1,), "start": (3,)}
    assert state.connection_occupancy == {Transit("start", "slow"): (2,)}
    assert state.in_flight == 1


def test_delivered_counts_the_drones_in_the_end_zone() -> None:
    timeline = make_timeline()

    assert timeline.state_at(2).delivered == 1
    assert timeline.state_at(3).delivered == 3


def test_finished_drones_stay_in_the_end_zone() -> None:
    state = make_timeline().state_at(3)

    assert state.zone_occupancy == {"goal": (1, 2, 3)}
    assert state.in_flight == 0


def test_state_at_clamps_out_of_range_turns() -> None:
    timeline = make_timeline()

    assert timeline.state_at(-5) is timeline.state_at(0)
    assert timeline.state_at(99) is timeline.state_at(timeline.last_turn)


def test_states_are_built_once_and_reused() -> None:
    timeline = make_timeline()

    assert timeline.state_at(1) is timeline.state_at(1)


def test_every_drone_is_counted_exactly_once_on_every_turn() -> None:
    timeline = make_timeline()

    for turn in range(timeline.last_turn + 1):
        state = timeline.state_at(turn)
        in_zones = sum(len(ids) for ids in state.zone_occupancy.values())

        assert in_zones + state.in_flight == 3


def test_occupancy_values_are_immutable() -> None:
    state = make_timeline().state_at(1)

    for ids in state.zone_occupancy.values():
        assert isinstance(ids, tuple)

    for ids in state.connection_occupancy.values():
        assert isinstance(ids, tuple)


def test_turn_state_reports_its_own_turn_index() -> None:
    timeline = make_timeline()

    for turn in range(timeline.last_turn + 1):
        assert timeline.state_at(turn).turn == turn


def test_a_single_waiting_drone_yields_a_static_timeline() -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "start"))
    timeline = SimulationTimeline(make_map(), schedule)

    assert timeline.last_turn == 1
    assert timeline.state_at(1) == TurnState(
        turn=1,
        zone_occupancy={"start": (1,)},
        connection_occupancy={},
        delivered=0,
        in_flight=0,
    )
