from dataclasses import dataclass

from fly_in.models import Map
from fly_in.routing import Transit, RouteSchedule, Location


@dataclass(frozen=True)
class TurnState:
    """Hold everything the visualizer needs to draw one turn."""

    turn: int
    zone_occupancy: dict[str, tuple[int, ...]]  # zone_name → drone_id
    connection_occupancy: dict[
        Transit, tuple[int, ...]
    ]  # connection → drone_id
    delivered: int
    in_flight: int


@dataclass
class SimulationTimeline:
    """Expose a route schedule as an indexable sequence of turn states."""

    def __init__(self, map: Map, schedule: RouteSchedule) -> None:
        self._map = map
        self._schedule = schedule
        self._states = tuple(
            self._build_state(turn) for turn in range(schedule.last_turn + 1)
        )

    @property
    def last_turn(self) -> int:
        """Return the index of the final turn."""

        return len(self._states) - 1

    def state_at(self, turn: int) -> TurnState:
        """Return the state of a turn, clamped to the valid range."""

        return self._states[max(0, min(self.last_turn, turn))]

    def _build_state(self, turn: int) -> TurnState:
        """Gather the position of every drone at one turn."""

        zones: dict[str, list[int]] = {}
        connections: dict[Transit, list[int]] = {}
        delivered = 0

        for drone_id in self._schedule.drone_ids:
            current = self._locate(drone_id, turn)

            if isinstance(current, Transit):
                connections.setdefault(current, []).append(drone_id)
                continue

            zones.setdefault(current, []).append(drone_id)

            if current == self._map.end:
                delivered += 1

        return TurnState(
            turn=turn,
            zone_occupancy={name: tuple(ids) for name, ids in zones.items()},
            connection_occupancy={
                connection: tuple(ids)
                for connection, ids in connections.items()
            },
            delivered=delivered,
            in_flight=sum(len(ids) for ids in connections.values()),
        )

    def _locate(self, drone_id: int, turn: int) -> Location:
        """Return a drone position, holding its last known location."""

        route = self._schedule.get_route(drone_id)

        return route[min(turn, len(route) - 1)]
