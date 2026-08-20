import asyncio

from typing import Awaitable, Callable, cast

import flet as ft

from fly_in.models import Map
from fly_in.routing import RouteSchedule

from .board import Board
from .controls import ControlBar
from .legend import Legend
from .theme import (
    BACKGROUND,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CHROME_HEIGHT,
    SPEEDS,
    TURN_SECONDS,
)
from .timeline import SimulationTimeline


class FlyInApp:
    """Drive the visualizer window."""

    def __init__(self, map: Map, schedule: RouteSchedule) -> None:
        timeline = SimulationTimeline(map, schedule)

        self._timeline = timeline
        self._total_drones = map.nb_drones
        self._turn = 0
        self._playing = False
        self._speed_index = SPEEDS.index(1.0)
        self._board = Board(map, timeline)
        self._status = ft.Text(self._status_text())
        self._legend = Legend()
        self._bar = ControlBar(
            timeline.last_turn,
            on_step=self._step,
            on_seek=self._seek,
            on_toggle=self._toggle,
            on_speed=self._next_speed,
        )

    def build(self, page: ft.Page) -> None:
        """Populate the page with the visualizer layout."""

        page.title = "Fly-in"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.bgcolor = BACKGROUND
        page.window.width = CANVAS_WIDTH
        page.window.height = CANVAS_HEIGHT + CHROME_HEIGHT
        page.on_keyboard_event = self._on_key
        page.on_resize = self._on_resize

        page.add(
            ft.Column(
                controls=[
                    self._board,
                    ft.Container(content=self._bar, padding=8),
                    ft.Container(content=self._legend, padding=8),
                    ft.Container(content=self._status, padding=8),
                ],
                spacing=0,
            )
        )
        page.run_task(self._center, page.window)

    @staticmethod
    async def _center(window: ft.Window) -> None:
        """Move the window to the middle of the screen.

        The desktop client answers this request only once it is running, so
        the layout is added first and a late or missing answer is ignored.
        """

        center = cast(Callable[[], Awaitable[None]], window.center)

        try:
            await center()
        except RuntimeError:
            pass

    def _status_text(self) -> str:
        """Return the status line for the current turn."""

        state = self._timeline.state_at(self._turn)

        return (
            f"Turn {self._turn} / {self._timeline.last_turn}   "
            f"Delivered {state.delivered} / {self._total_drones}   "
            f"In flight {state.in_flight}"
        )

    def _interval(self) -> float:
        """Return how long one turn lasts at the current speed."""

        return TURN_SECONDS / SPEEDS[self._speed_index]

    def _step(self, delta: int) -> None:
        """Move by the given number of turns, stopping the playback."""

        self._seek(self._turn + delta)

    def _seek(self, turn: int) -> None:
        """Jump to a turn, stopping the playback."""

        self._set_playing(False)
        self._go_to(turn)

    def _toggle(self) -> None:
        """Start the playback, or stop it while it runs."""

        if not self._playing and self._turn >= self._timeline.last_turn:
            self._go_to(0)

        self._set_playing(not self._playing)

    def _next_speed(self) -> None:
        """Switch to the next playback speed."""

        self._speed_index = (self._speed_index + 1) % len(SPEEDS)
        self._bar.set_speed(SPEEDS[self._speed_index])
        self._board.set_interval(self._interval())

    def _set_playing(self, playing: bool) -> None:
        """Start or stop the playback loop."""

        if playing == self._playing:
            return

        self._playing = playing
        self._bar.set_playing(playing)

        if playing:
            asyncio.ensure_future(self._play_loop())

    async def _play_loop(self) -> None:
        """Advance one turn at a time until paused or finished."""

        while self._playing:
            await asyncio.sleep(self._interval())

            if not self._playing:
                return

            if self._turn >= self._timeline.last_turn:
                self._set_playing(False)
                return

            self._go_to(self._turn + 1)

    def _go_to(self, turn: int) -> None:
        """Show the given turn, ignoring turns outside the schedule."""

        turn = max(0, min(self._timeline.last_turn, turn))

        if turn == self._turn:
            return

        self._turn = turn
        self._board.show_turn(turn)
        self._bar.set_turn(turn)
        self._status.value = self._status_text()
        self._status.update()

    def _on_resize(self, e: ft.PageResizeEvent) -> None:
        """Refit the map when the window changes size."""

        self._board.resize(int(e.width), int(e.height) - CHROME_HEIGHT)

    def _on_key(self, e: ft.KeyboardEvent) -> None:
        """Move through turns with the keyboard."""

        if e.key == "Arrow Right":
            self._step(1)
        elif e.key == "Arrow Left":
            self._step(-1)
        elif e.key in (" ", "Space"):
            self._toggle()
        elif e.key == "Home":
            self._seek(0)


def render_app(map: Map, schedule: RouteSchedule) -> None:
    """Open the visualizer window and block until it is closed."""

    ft.run(FlyInApp(map, schedule).build)
