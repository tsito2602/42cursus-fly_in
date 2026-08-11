from dataclasses import dataclass, field
from typing import TypeAlias
from itertools import pairwise

from fly_in.models import Connection, Zone


@dataclass(frozen=True)
class Transit:
    origin: str
    destination: str


Location: TypeAlias = str | Transit
Route: TypeAlias = tuple[Location, ...]
ZoneSlot: TypeAlias = tuple[int, str]
ConnectionSlot: TypeAlias = tuple[int, str, str]


@dataclass
class RouteSchedule:
    _routes: dict[int, Route] = field(default_factory=dict)
    _zone_usage: dict[ZoneSlot, int] = field(default_factory=dict)
    _connection_usage: dict[ConnectionSlot, int] = field(default_factory=dict)

    def add_route(self, drone_id: int, route: Route) -> None:
        if drone_id in self._routes:
            raise ValueError(f"Drone {drone_id} already has a route.")

        self._routes[drone_id] = route
        self._reserve_zones(route)
        self._reserve_connections(route)

    def get_route(self, drone_id: int) -> Route:
        if drone_id not in self._routes:
            raise ValueError(f"Drone {drone_id} does not have a route.")

        return self._routes[drone_id]

    def can_enter_zone(self, turn: int, zone: Zone) -> bool:
        if zone.capacity is None:
            return True

        usage = self._zone_usage.get((turn, zone.name), 0)
        return usage < zone.capacity

    def can_use_connection(self, turn: int, connection: Connection) -> bool:
        slot = self._connection_slot(
            turn, connection.zone_a, connection.zone_b
        )

        usage = self._connection_usage.get(slot, 0)
        return usage < connection.capacity

    def _reserve_zones(self, route: Route) -> None:
        for turn, location in enumerate(route):
            if isinstance(location, Transit):
                continue

            slot = (turn, location)
            self._zone_usage[slot] = self._zone_usage.get(slot, 0) + 1

    def _reserve_connections(self, route: Route) -> None:
        for turn, locations in enumerate(pairwise(route)):
            current, next = locations

            connection = self._connection_for_interval(current, next)
            if connection is None:
                continue

            zone_a, zone_b = connection
            slot: ConnectionSlot = self._connection_slot(turn, zone_a, zone_b)
            self._connection_usage[slot] = (
                self._connection_usage.get(slot, 0) + 1
            )

    @staticmethod
    def _connection_for_interval(
        current: Location, next: Location
    ) -> tuple[str, str] | None:
        if isinstance(current, Transit):
            return current.origin, current.destination

        if isinstance(next, Transit):
            return next.origin, next.destination

        if current == next:
            return None

        return current, next

    @staticmethod
    def _connection_slot(
        turn: int, zone_a: str, zone_b: str
    ) -> ConnectionSlot:
        first, second = sorted((zone_a, zone_b))
        return turn, first, second
