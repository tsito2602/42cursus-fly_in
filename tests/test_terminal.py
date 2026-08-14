import pytest

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.rendering import render_schedule
from fly_in.routing import RouteSchedule, Transit


def make_map(
    nb_drones: int,
    colors: dict[str, str] | None = None,
) -> Map:
    colors = colors or {}
    zones = {
        "start": Zone(
            name="start",
            x=0,
            y=0,
            zone_role=ZoneRole.START,
            color=colors.get("start"),
            capacity=None,
        ),
        "hub": Zone(
            name="hub",
            x=1,
            y=0,
            zone_role=ZoneRole.HUB,
            color=colors.get("hub"),
        ),
        "restricted": Zone(
            name="restricted",
            x=1,
            y=1,
            zone_role=ZoneRole.HUB,
            zone_type=ZoneType.RESTRICTED,
            color=colors.get("restricted"),
        ),
        "goal": Zone(
            name="goal",
            x=2,
            y=0,
            zone_role=ZoneRole.END,
            color=colors.get("goal"),
            capacity=None,
        ),
    }

    return Map(
        nb_drones=nb_drones,
        zones=zones,
        connections=[],
        start="start",
        end="goal",
    )


def test_renders_movements_by_turn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=2)
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))
    schedule.add_route(2, ("start", "start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == (
        "D1-hub\n"
        "D1-goal D2-hub\n"
        "D2-goal\n"
    )


def test_renders_transit_as_connection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(
        nb_drones=1,
        colors={"start": "green", "restricted": "red"},
    )
    schedule = RouteSchedule()
    schedule.add_route(
        1,
        (
            "start",
            Transit("start", "restricted"),
            "restricted",
            "goal",
        ),
    )

    render_schedule(map, schedule)

    assert capsys.readouterr().out == (
        "D1-\033[32mstart\033[0m-\033[31mrestricted\033[0m\n"
        "D1-\033[31mrestricted\033[0m\n"
        "D1-goal\n"
    )


def test_renders_zone_with_ansi_color(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=1, colors={"hub": "blue"})
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == (
        "D1-\033[34mhub\033[0m\n"
        "D1-goal\n"
    )


def test_renders_unsupported_color_without_ansi_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=1, colors={"hub": "orange"})
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == "D1-hub\nD1-goal\n"
