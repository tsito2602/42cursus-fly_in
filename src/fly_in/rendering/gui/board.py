import flet as ft

from fly_in.models import Map

from .crowd_badge import CrowdBadge
from .drone_layout import DroneLayout
from .drone_marker import DroneMarker
from .geometry import Point
from .link_hotspot import LinkHotspot
from .network import NetworkCanvas
from .rainbow_zone import RainbowZone
from .theme import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MIN_CANVAS_HEIGHT,
    MIN_CANVAS_WIDTH,
    TURN_SECONDS,
    animation_ms,
    crowd_font,
    crowd_radius,
    drawn_radius,
    drone_radius,
    is_rainbow,
)
from .timeline import SimulationTimeline
from .transform import ViewTransform
from .zone_hotspot import ZoneHotspot


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
            *self._make_link_hotspots(transform),
            *self._make_zone_hotspots(transform),
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

    def _make_link_hotspots(
        self, transform: ViewTransform
    ) -> list[LinkHotspot]:
        """Return the hover area lying along every connection line."""

        hotspots: list[LinkHotspot] = []

        for connection in self._map.connections:
            zone_a = self._map.zones[connection.zone_a]
            zone_b = self._map.zones[connection.zone_b]

            hotspots.append(
                LinkHotspot(
                    connection,
                    transform.to_pixel(zone_a.x, zone_a.y),
                    transform.to_pixel(zone_b.x, zone_b.y),
                )
            )

        return hotspots

    def _make_zone_hotspots(
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
