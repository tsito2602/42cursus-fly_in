from collections.abc import Iterator
import math

from fly_in.models import Map
from fly_in.routing import Transit

from .theme import CROWD_THRESHOLD, drone_radius
from .timeline import SimulationTimeline, TurnState
from .transform import Point, ViewTransform


class DroneLayout:
    """Turn each drone location into a pixel point, turn by turn."""

    def __init__(
        self, map: Map, timeline: SimulationTimeline, transform: ViewTransform
    ) -> None:
        self._map = map
        self._transform = transform
        self._spacing = drone_radius(transform.scale) * 2.4

        turns = [
            self._build_turn(timeline.state_at(turn))
            for turn in range(timeline.last_turn + 1)
        ]

        self._points: tuple[dict[int, Point], ...] = tuple(
            points for points, _ in turns
        )
        self._crowds: tuple[dict[Point, int], ...] = tuple(
            crowds for _, crowds in turns
        )

    def points_at(self, turn: int) -> dict[int, Point]:
        """Return the pixel point of every drone on one turn."""

        return self._points[self._clamp(turn)]

    def crowds_at(self, turn: int) -> dict[Point, int]:
        """Return how many drones are stacked on each crowded point."""

        return self._crowds[self._clamp(turn)]

    def crowd_points(self) -> tuple[Point, ...]:
        """Return every point that holds a crowd on at least one turn."""

        points = {point for crowds in self._crowds for point in crowds}

        return tuple(sorted(points))

    def _clamp(self, turn: int) -> int:
        """Return a turn index that exists in the schedule."""

        return max(0, min(len(self._points) - 1, turn))

    def _build_turn(
        self, state: TurnState
    ) -> tuple[dict[int, Point], dict[Point, int]]:
        """Return the points and the crowds of one turn."""

        points: dict[int, Point] = {}
        crowds: dict[Point, int] = {}

        for center, drone_ids in self._groups(state):
            points.update(self._cluster(center, drone_ids))

            if len(drone_ids) >= CROWD_THRESHOLD:
                crowds[center] = len(drone_ids)

        return points, crowds

    def _groups(
        self, state: TurnState
    ) -> Iterator[tuple[Point, tuple[int, ...]]]:
        """Yield each occupied location with the drones sitting on it."""

        for name, drone_ids in state.zone_occupancy.items():
            zone = self._map.zones[name]

            yield self._transform.to_pixel(zone.x, zone.y), drone_ids

        for transit, drone_ids in state.connection_occupancy.items():
            yield self._midpoint(transit), drone_ids

    def _cluster(
        self, center: Point, drone_ids: tuple[int, ...]
    ) -> dict[int, Point]:
        """Draw a polygon of drones, or stack them when crowded."""

        if len(drone_ids) >= CROWD_THRESHOLD:
            return {drone_id: center for drone_id in drone_ids}

        if len(drone_ids) == 1:
            return {drone_ids[0]: center}

        return {
            drone_id: self._corner(center, index, len(drone_ids))
            for index, drone_id in enumerate(drone_ids)
        }

    def _corner(self, center: Point, index: int, sides: int) -> Point:
        """Return one corner of the polygon drawn around a location."""

        center_x, center_y = center
        start = 0.0 if sides == 2 else -math.pi / 2.0
        angle = 2.0 * math.pi * index / sides + start

        return (
            center_x + self._spacing * math.cos(angle),
            center_y + self._spacing * math.sin(angle),
        )

    def _midpoint(self, transit: Transit) -> Point:
        """Return the pixel midpoint of a connection."""

        origin = self._map.zones[transit.origin]
        destination = self._map.zones[transit.destination]

        x1, y1 = self._transform.to_pixel(origin.x, origin.y)
        x2, y2 = self._transform.to_pixel(destination.x, destination.y)

        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
