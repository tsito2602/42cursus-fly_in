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
        "D1-\033[38;2;0;128;0mstart\033[0m-"
        "\033[38;2;255;0;0mrestricted\033[0m\n"
        "D1-\033[38;2;255;0;0mrestricted\033[0m\n"
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
        "D1-\033[38;2;0;0;255mhub\033[0m\n"
        "D1-goal\n"
    )


@pytest.mark.parametrize(
    ("color", "rgb"),
    [
        ("black", "0;0;0"),
        ("blue", "0;0;255"),
        ("brown", "165;42;42"),
        ("crimson", "220;20;60"),
        ("cyan", "0;255;255"),
        ("darkred", "139;0;0"),
        ("gold", "255;215;0"),
        ("green", "0;128;0"),
        ("lime", "0;255;0"),
        ("magenta", "255;0;255"),
        ("maroon", "128;0;0"),
        ("orange", "255;165;0"),
        ("purple", "128;0;128"),
        ("red", "255;0;0"),
        ("violet", "238;130;238"),
        ("yellow", "255;255;0"),
    ],
)
def test_renders_map_color_as_rgb(
    color: str,
    rgb: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=1, colors={"hub": color})
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == (
        f"D1-\033[38;2;{rgb}mhub\033[0m\nD1-goal\n"
    )


def test_renders_rainbow_color(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=1, colors={"hub": "rainbow"})
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == (
        "D1-\033[38;2;255;0;0mh"
        "\033[38;2;255;165;0mu"
        "\033[38;2;255;255;0mb\033[0m\n"
        "D1-goal\n"
    )


def test_renders_unsupported_color_without_rgb_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    map = make_map(nb_drones=1, colors={"hub": "unknown"})
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))

    render_schedule(map, schedule)

    assert capsys.readouterr().out == "D1-hub\nD1-goal\n"
