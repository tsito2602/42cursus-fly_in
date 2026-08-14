import pytest

from fly_in.rendering import render_schedule
from fly_in.routing import RouteSchedule, Transit


def test_renders_movements_by_turn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))
    schedule.add_route(2, ("start", "start", "hub", "goal"))

    render_schedule(schedule, nb_drones=2)

    assert capsys.readouterr().out == (
        "D1-hub\n"
        "D1-goal D2-hub\n"
        "D2-goal\n"
    )


def test_renders_transit_as_connection(
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    render_schedule(schedule, nb_drones=1)

    assert capsys.readouterr().out == (
        "D1-start-restricted\n"
        "D1-restricted\n"
        "D1-goal\n"
    )
