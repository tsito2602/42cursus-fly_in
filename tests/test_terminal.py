import pytest

from fly_in.rendering import render_schedule
from fly_in.routing import RouteSchedule, Transit


def test_renders_movements_by_turn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "hub", "goal"))
    schedule.add_route(2, ("start", "start", "hub", "goal"))

    render_schedule(schedule)

    assert capsys.readouterr().out == (
        "D1-hub\n"
        "D1-goal D2-hub\n"
        "D2-goal\n"
    )


def test_renders_transit_as_a_connection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(
        1,
        ("start", Transit("start", "restricted"), "restricted", "goal"),
    )

    render_schedule(schedule)

    assert capsys.readouterr().out == (
        "D1-start-restricted\n"
        "D1-restricted\n"
        "D1-goal\n"
    )


def test_the_initial_placement_is_not_printed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "goal"))

    render_schedule(schedule)

    assert capsys.readouterr().out == "D1-goal\n"


def test_a_waiting_drone_is_omitted_from_its_turn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "start", "goal"))
    schedule.add_route(2, ("start", "goal"))

    render_schedule(schedule)

    assert capsys.readouterr().out == (
        "D2-goal\n"
        "D1-goal\n"
    )


def test_a_delivered_drone_is_no_longer_tracked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "goal"))
    schedule.add_route(2, ("start", "hub", "goal"))

    render_schedule(schedule)

    assert capsys.readouterr().out == (
        "D1-goal D2-hub\n"
        "D2-goal\n"
    )


def test_drones_are_listed_in_ascending_id_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(3, ("start", "goal"))
    schedule.add_route(1, ("start", "goal"))
    schedule.add_route(2, ("start", "goal"))

    render_schedule(schedule)

    assert capsys.readouterr().out == "D1-goal D2-goal D3-goal\n"


def test_no_output_is_produced_without_any_movement(
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start",))

    render_schedule(schedule)

    assert "D" not in capsys.readouterr().out
