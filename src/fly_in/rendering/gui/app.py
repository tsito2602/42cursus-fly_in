import asyncio

from typing import Awaitable, Callable, cast

import flet as ft

from fly_in.models import Connection, Map
from fly_in.routing import RouteSchedule

from .controls import ControlBar
from .crowd_badge import CrowdBadge
from .legend import Legend
from .network import NetworkCanvas
from .theme import (
    BACKGROUND,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CHROME_HEIGHT,
    MIN_CANVAS_HEIGHT,
    MIN_CANVAS_WIDTH,
    SPEEDS,
    TURN_SECONDS,
    animation_ms,
    crowd_font,
    crowd_radius,
    drawn_radius,
    drone_radius,
    is_rainbow,
)
from .timeline import SimulationTimeline
from .link_hotspot import LinkHotspot
from .rainbow_zone import RainbowZone
from .zone_hotspot import ZoneHotspot
from .view_transform import ViewTransform
from .drone_layout import DroneLayout, Point
from .drone_marker import DroneMarker


class Board(ft.Stack):
    """Hold the static map and the animated drone markers."""

    def __init__(self, map: Map, timeline: SimulationTimeline) -> None:
        self._map = map
        self._timeline = timeline
        self._width = CANVAS_WIDTH
        self._height = CANVAS_HEIGHT
        self._turn = 0
        self._interval = TURN_SECONDS

        super().__init__(width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
        self._rebuild()

    def show_turn(self, turn: int) -> None:
        """Move every marker to its position on the given turn."""

        self._turn = turn

        for drone_id, point in self._layout.points_at(turn).items():
            self._markers[drone_id].move_to(point)

        self._show_crowds()
        self.update()

    def set_interval(self, interval: float) -> None:
        """Keep every marker animation shorter than one turn."""

        self._interval = interval
        milliseconds = animation_ms(interval)

        for marker in self._markers.values():
            marker.set_duration(milliseconds)

        self.update()

    def resize(self, width: int, height: int) -> None:
        """Redraw the whole board at a new canvas size."""

        self._width = max(MIN_CANVAS_WIDTH, width)
        self._height = max(MIN_CANVAS_HEIGHT, height)
        self.width = self._width
        self.height = self._height
        self._rebuild()
        self.update()

    def _rebuild(self) -> None:
        """Recompute every pixel coordinate for the current size."""

        transform = ViewTransform(
            self._map.zones.values(), self._width, self._height
        )
        self._layout = DroneLayout(self._map, self._timeline, transform)
        self._markers = self._make_markers(transform)
        self._badges = self._make_badges(transform)
        self.controls = [
            NetworkCanvas(self._map, transform, self._width, self._height),
            *self._make_rainbows(transform),
            *self._make_links(transform),
            *self._make_hotspots(transform),
            *self._markers.values(),
            *self._badges.values(),
        ]
        self._show_crowds()

    def _make_rainbows(
        self, transform: ViewTransform
    ) -> list[RainbowZone]:
        """Return the gradient covering every rainbow zone."""

        return [
            RainbowZone(
                zone,
                drawn_radius(zone, transform.scale),
                transform.to_pixel(zone.x, zone.y),
            )
            for zone in self._map.zones.values()
            if is_rainbow(zone)
        ]

    def _make_links(self, transform: ViewTransform) -> list[LinkHotspot]:
        """Return the hover area covering every connection line."""

        return [
            self._link(connection, transform)
            for connection in self._map.connections
        ]

    def _link(
        self, connection: Connection, transform: ViewTransform
    ) -> LinkHotspot:
        """Return the hover area lying along one connection line."""

        zone_a = self._map.zones[connection.zone_a]
        zone_b = self._map.zones[connection.zone_b]

        return LinkHotspot(
            connection,
            transform.to_pixel(zone_a.x, zone_a.y),
            transform.to_pixel(zone_b.x, zone_b.y),
        )

    def _make_hotspots(
        self, transform: ViewTransform
    ) -> list[ZoneHotspot]:
        """Return the hover area covering every zone circle."""

        return [
            ZoneHotspot(
                zone,
                drawn_radius(zone, transform.scale),
                transform.to_pixel(zone.x, zone.y),
            )
            for zone in self._map.zones.values()
        ]

    def _make_markers(
        self, transform: ViewTransform
    ) -> dict[int, DroneMarker]:
        """Return a fresh marker for every drone at the current turn."""

        radius = drone_radius(transform.scale)
        milliseconds = animation_ms(self._interval)
        markers: dict[int, DroneMarker] = {}

        for drone_id, point in self._layout.points_at(self._turn).items():
            marker = DroneMarker(drone_id, radius, point)
            marker.set_duration(milliseconds)
            markers[drone_id] = marker

        return markers

    def _make_badges(
        self, transform: ViewTransform
    ) -> dict[Point, CrowdBadge]:
        """Return a hidden count badge for every crowded location."""

        radius = crowd_radius(transform.scale)
        font = crowd_font(transform.scale)

        return {
            point: CrowdBadge(radius, font, point)
            for point in self._layout.crowd_points()
        }

    def _show_crowds(self) -> None:
        """Update the count badge of every crowded location."""

        crowds = self._layout.crowds_at(self._turn)

        for point, badge in self._badges.items():
            badge.set_count(crowds.get(point, 0))


class FlyInApp:
    """Drive the visualizer window."""

    def __init__(self, map: Map, schedule: RouteSchedule) -> None:
        timeline = SimulationTimeline(map, schedule)

        self._timeline = timeline
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
            f"Delivered {state.delivered}   In flight {state.in_flight}"
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
