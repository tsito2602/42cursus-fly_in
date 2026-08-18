"""Test turn switching in the visualizer window."""

import asyncio

from typing import Any, Coroutine, Iterator, cast

import flet as ft
import pytest

from fly_in.models import Map, Zone, ZoneRole, ZoneType
from fly_in.models.connection import Connection
from fly_in.rendering.gui.app import Board, FlyInApp
from fly_in.rendering.gui.drone_layout import DroneLayout, Point
from fly_in.rendering.gui.crowd_badge import CrowdBadge
from fly_in.rendering.gui.drone_marker import DroneMarker
from fly_in.rendering.gui.zone_hotspot import ZoneHotspot
from fly_in.rendering.gui.theme import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CHROME_HEIGHT,
    CROWD_THRESHOLD,
    MIN_CANVAS_HEIGHT,
    MIN_CANVAS_WIDTH,
    DRONE_OUTLINE,
    SPEEDS,
    animation_ms,
    drawn_radius,
    drone_radius,
    zone_details,
    outline_width,
)
from fly_in.rendering.gui.timeline import SimulationTimeline
from fly_in.rendering.gui.view_transform import ViewTransform
from fly_in.routing import RouteSchedule, Transit


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
        make_zone("middle", 2, 0, ZoneRole.HUB),
        make_zone("goal", 4, 0, ZoneRole.END),
    )

    return Map(
        nb_drones=2,
        zones={zone.name: zone for zone in zones},
        connections=[
            Connection(zone_a="start", zone_b="middle"),
            Connection(zone_a="middle", zone_b="goal"),
        ],
        start="start",
        end="goal",
    )


def make_schedule() -> RouteSchedule:
    schedule = RouteSchedule()
    schedule.add_route(1, ("start", "middle", "goal"))
    schedule.add_route(
        2, ("start", Transit("start", "middle"), "middle", "goal")
    )

    return schedule


def make_app() -> FlyInApp:
    return FlyInApp(make_map(), make_schedule())


def make_transform() -> ViewTransform:
    return ViewTransform(
        make_map().zones.values(), CANVAS_WIDTH, CANVAS_HEIGHT
    )


def make_board() -> tuple[Board, DroneLayout, int]:
    """Return a board, a matching layout, and the last turn."""

    map = make_map()
    timeline = SimulationTimeline(map, make_schedule())
    layout = DroneLayout(map, timeline, make_transform())

    return Board(map, timeline), layout, timeline.last_turn


def make_crowd_board() -> Board:
    """Return a board whose drones all start on the same zone."""

    map = make_map()
    map.nb_drones = CROWD_THRESHOLD
    schedule = RouteSchedule()

    for drone_id in range(1, CROWD_THRESHOLD + 1):
        schedule.add_route(drone_id, ("start", "middle", "goal"))

    return Board(map, SimulationTimeline(map, schedule))


def badges_of(board: Board) -> list[CrowdBadge]:
    """Return every crowd badge on the board."""

    return [
        control
        for control in board.controls
        if isinstance(control, CrowdBadge)
    ]


def make_layout(width: int, height: int) -> DroneLayout:
    """Return the layout a board of the given size should produce."""

    map = make_map()
    timeline = SimulationTimeline(map, make_schedule())
    transform = ViewTransform(map.zones.values(), width, height)

    return DroneLayout(map, timeline, transform)


def markers_of(board: Board) -> list[DroneMarker]:
    """Return every drone marker on the board, in drawing order."""

    return [
        control
        for control in board.controls
        if isinstance(control, DroneMarker)
    ]


def centers_of(board: Board) -> dict[int, Point]:
    """Return the center point of every marker on the board."""

    radius = drone_radius(make_transform().scale)
    markers = markers_of(board)

    return {
        index: (control.left + radius, control.top + radius)
        for index, control in enumerate(markers, start=1)
        if control.left is not None and control.top is not None
    }


def press(app: FlyInApp, key: str) -> None:
    app._on_key(
        ft.KeyboardEvent(
            name="keyboard_event",
            control=cast(ft.Page, app._board),
            key=key,
            shift=False,
            ctrl=False,
            alt=False,
            meta=False,
        )
    )


def test_a_board_starts_on_turn_zero() -> None:
    board, layout, last_turn = make_board()

    assert centers_of(board) == layout.points_at(0)


def test_show_turn_moves_every_marker() -> None:
    board, layout, last_turn = make_board()

    board.show_turn(2)

    assert centers_of(board) == layout.points_at(2)


def test_show_turn_can_go_backwards() -> None:
    board, layout, last_turn = make_board()

    board.show_turn(3)
    board.show_turn(1)

    assert centers_of(board) == layout.points_at(1)


def test_show_turn_clamps_a_turn_past_the_end() -> None:
    board, layout, last_turn = make_board()

    board.show_turn(99)

    assert centers_of(board) == layout.points_at(last_turn)


def test_a_new_app_starts_on_the_first_turn() -> None:
    app = make_app()

    assert app._turn == 0
    assert app._playing is False


def test_the_right_arrow_advances_one_turn() -> None:
    app = make_app()

    press(app, "Arrow Right")

    assert app._turn == 1


def test_the_left_arrow_goes_back_one_turn() -> None:
    app = make_app()

    press(app, "Arrow Right")
    press(app, "Arrow Right")
    press(app, "Arrow Left")

    assert app._turn == 1


def test_the_left_arrow_stops_at_the_first_turn() -> None:
    app = make_app()

    press(app, "Arrow Left")

    assert app._turn == 0


def test_the_right_arrow_stops_at_the_last_turn() -> None:
    app = make_app()

    for _ in range(20):
        press(app, "Arrow Right")

    assert app._turn == app._timeline.last_turn


def test_an_unbound_key_changes_nothing() -> None:
    app = make_app()

    press(app, "Arrow Right")
    press(app, "Arrow Up")

    assert app._turn == 1


def test_the_home_key_returns_to_the_first_turn() -> None:
    app = make_app()

    press(app, "Arrow Right")
    press(app, "Arrow Right")
    press(app, "Home")

    assert app._turn == 0


def test_moving_a_turn_moves_the_markers() -> None:
    app = make_app()

    press(app, "Arrow Right")

    _, layout, _ = make_board()

    assert centers_of(app._board) == layout.points_at(1)


def test_the_status_reports_the_current_turn() -> None:
    app = make_app()

    press(app, "Arrow Right")

    assert app._status.value is not None
    assert app._status.value.startswith("Turn 1 / 3")


def test_the_status_counts_delivered_drones() -> None:
    app = make_app()

    for _ in range(3):
        press(app, "Arrow Right")

    assert app._status.value == "Turn 3 / 3   Delivered 2   In flight 0"


def test_the_status_counts_drones_in_flight() -> None:
    app = make_app()

    press(app, "Arrow Right")

    assert app._status.value == "Turn 1 / 3   Delivered 0   In flight 1"


def run(work: Coroutine[Any, Any, None]) -> None:
    """Run one coroutine on a fresh event loop."""

    asyncio.run(work)


def test_the_space_key_starts_the_playback() -> None:
    app = make_app()

    async def work() -> None:
        press(app, " ")

        assert app._playing is True

        app._set_playing(False)

    run(work())


def test_the_playback_advances_by_itself() -> None:
    app = make_app()

    async def work() -> None:
        app._speed_index = SPEEDS.index(4.0)
        press(app, "Space")

        await asyncio.sleep(app._interval() * 1.5)
        app._set_playing(False)

        assert app._turn == 1

    run(work())


def test_the_space_key_stops_a_running_playback() -> None:
    app = make_app()

    async def work() -> None:
        press(app, " ")
        press(app, " ")

        assert app._playing is False

        await asyncio.sleep(app._interval() * 1.5)

        assert app._turn == 0

    run(work())


def test_the_playback_stops_on_the_last_turn() -> None:
    app = make_app()

    async def work() -> None:
        app._speed_index = SPEEDS.index(4.0)
        app._go_to(app._timeline.last_turn - 1)
        app._set_playing(True)

        await asyncio.sleep(app._interval() * 3.0)

        assert app._turn == app._timeline.last_turn
        assert app._playing is False

    run(work())


def test_the_playback_restarts_from_the_first_turn() -> None:
    app = make_app()

    async def work() -> None:
        app._go_to(app._timeline.last_turn)
        app._toggle()

        assert app._turn == 0
        assert app._playing is True

        app._set_playing(False)

    run(work())


def test_seeking_stops_the_playback() -> None:
    app = make_app()

    async def work() -> None:
        app._set_playing(True)
        app._seek(2)

        assert app._playing is False
        assert app._turn == 2

    run(work())


def test_starting_twice_leaves_one_loop() -> None:
    app = make_app()

    async def work() -> None:
        app._speed_index = SPEEDS.index(4.0)
        app._set_playing(True)
        app._set_playing(True)

        await asyncio.sleep(app._interval() * 1.5)
        app._set_playing(False)

        assert app._turn == 1

    run(work())


def test_the_speed_button_cycles_through_the_speeds() -> None:
    app = make_app()
    speeds = []

    for _ in range(len(SPEEDS) + 1):
        speeds.append(SPEEDS[app._speed_index])
        app._next_speed()

    assert speeds == [1.0, 2.0, 4.0, 0.5, 1.0]


def test_a_faster_speed_shortens_the_turn() -> None:
    app = make_app()
    slow = app._interval()

    app._next_speed()

    assert app._interval() == slow / 2.0


def test_a_faster_speed_shortens_the_animation() -> None:
    app = make_app()

    app._next_speed()

    marker = next(
        control
        for control in app._board.controls
        if isinstance(control, DroneMarker)
    )

    animation = marker.animate_position

    assert isinstance(animation, ft.Animation)
    assert animation.duration == animation_ms(app._interval())


def test_resizing_keeps_every_drone() -> None:
    board, _, _ = make_board()

    board.resize(800, 500)

    assert len(markers_of(board)) == make_map().nb_drones


def test_resizing_refits_the_map() -> None:
    board, _, _ = make_board()

    board.resize(800, 500)

    radius = drone_radius(ViewTransform(
        make_map().zones.values(), 800, 500
    ).scale)
    centers = {
        index: (marker.left + radius, marker.top + radius)
        for index, marker in enumerate(markers_of(board), start=1)
        if marker.left is not None and marker.top is not None
    }

    assert centers == make_layout(800, 500).points_at(0)


def test_resizing_keeps_the_current_turn() -> None:
    board, _, _ = make_board()

    board.show_turn(2)
    board.resize(800, 500)

    radius = drone_radius(ViewTransform(
        make_map().zones.values(), 800, 500
    ).scale)
    centers = {
        index: (marker.left + radius, marker.top + radius)
        for index, marker in enumerate(markers_of(board), start=1)
        if marker.left is not None and marker.top is not None
    }

    assert centers == make_layout(800, 500).points_at(2)


def test_resizing_keeps_the_animation_length() -> None:
    board, _, _ = make_board()

    board.set_interval(0.15)
    board.resize(800, 500)

    for marker in markers_of(board):
        animation = marker.animate_position

        assert isinstance(animation, ft.Animation)
        assert animation.duration == animation_ms(0.15)


def test_a_tiny_window_does_not_flip_the_map() -> None:
    board, _, last_turn = make_board()

    board.resize(10, 10)

    for turn in range(last_turn + 1):
        board.show_turn(turn)

        for marker in markers_of(board):
            assert marker.left is not None and marker.top is not None
            assert 0.0 <= marker.left <= MIN_CANVAS_WIDTH
            assert 0.0 <= marker.top <= MIN_CANVAS_HEIGHT


def test_resizing_the_window_resizes_the_board() -> None:
    app = make_app()

    app._on_resize(
        ft.PageResizeEvent(
            name="resize",
            data=None,
            control=cast(ft.Page, app._board),
            width=900.0,
            height=600.0,
        )
    )

    assert app._board.width == 900
    assert app._board.height == 600 - CHROME_HEIGHT


def test_an_uncrowded_board_carries_no_badge() -> None:
    board, _, _ = make_board()

    assert badges_of(board) == []


def test_a_crowd_shows_its_count() -> None:
    board = make_crowd_board()
    badges = badges_of(board)

    assert len(badges) == 3
    assert [badge.visible for badge in badges].count(True) == 1

    shown = next(badge for badge in badges if badge.visible)
    text = shown.content

    assert isinstance(text, ft.Text)
    assert text.value == str(CROWD_THRESHOLD)


def test_a_badge_hides_when_the_crowd_moves_on() -> None:
    board = make_crowd_board()
    start = next(badge for badge in badges_of(board) if badge.visible)

    board.show_turn(1)

    assert start.visible is False


def test_a_badge_sits_behind_no_drone() -> None:
    board = make_crowd_board()
    controls = board.controls
    markers = [
        index
        for index, control in enumerate(controls)
        if isinstance(control, DroneMarker)
    ]
    badges = [
        index
        for index, control in enumerate(controls)
        if isinstance(control, CrowdBadge)
    ]

    assert min(badges) > max(markers)


def test_a_crowd_stacks_every_drone_on_one_point() -> None:
    board = make_crowd_board()
    corners = {
        (marker.left, marker.top) for marker in markers_of(board)
    }

    assert len(corners) == 1


def test_resizing_keeps_the_badges() -> None:
    board = make_crowd_board()

    board.resize(800, 500)
    badges = badges_of(board)

    assert len(badges) == 3
    assert [badge.visible for badge in badges].count(True) == 1


def test_every_drone_carries_a_dark_outline() -> None:
    board, _, _ = make_board()

    for marker in markers_of(board):
        border = marker.border

        assert border is not None
        assert border.top is not None
        assert border.top.color == DRONE_OUTLINE
        assert border.top.width == outline_width(
            float(marker.height or 0.0) / 2.0
        )


def test_every_badge_carries_a_dark_outline() -> None:
    board = make_crowd_board()

    for badge in badges_of(board):
        border = badge.border

        assert border is not None
        assert border.top is not None
        assert border.top.color == DRONE_OUTLINE


def hotspots_of(board: Board) -> list[ZoneHotspot]:
    """Return the hover area of every zone."""

    return [
        control
        for control in board.controls
        if isinstance(control, ZoneHotspot)
    ]


def test_every_zone_carries_a_hover_area() -> None:
    board, _, _ = make_board()

    assert len(hotspots_of(board)) == len(make_map().zones)


def test_a_hover_area_shows_the_details_of_its_zone() -> None:
    board, _, _ = make_board()
    map = make_map()
    tooltips = [hotspot.tooltip for hotspot in hotspots_of(board)]

    assert tooltips == [
        zone_details(zone) for zone in map.zones.values()
    ]


def test_a_hover_area_covers_its_zone_circle() -> None:
    board, _, _ = make_board()
    map = make_map()
    transform = make_transform()

    for hotspot, zone in zip(hotspots_of(board), map.zones.values()):
        radius = drawn_radius(zone, transform.scale)
        x, y = transform.to_pixel(zone.x, zone.y)

        assert hotspot.width == radius * 2.0
        assert hotspot.left == x - radius
        assert hotspot.top == y - radius


def test_a_hover_area_stays_under_the_drones() -> None:
    board, _, _ = make_board()
    controls = board.controls
    hotspots = [
        index
        for index, control in enumerate(controls)
        if isinstance(control, ZoneHotspot)
    ]
    markers = [
        index
        for index, control in enumerate(controls)
        if isinstance(control, DroneMarker)
    ]

    assert max(hotspots) < min(markers)


def test_a_resize_moves_every_hover_area() -> None:
    board, _, _ = make_board()
    before = [hotspot.left for hotspot in hotspots_of(board)]

    board.resize(600, 400)

    assert [hotspot.left for hotspot in hotspots_of(board)] != before
    assert len(hotspots_of(board)) == len(make_map().zones)
