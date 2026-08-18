"""Store planned routes and their capacity reservations."""

from dataclasses import dataclass, field
from typing import TypeAlias
from itertools import pairwise

from fly_in.models import Connection, Zone


@dataclass(frozen=True)
class Transit:
    """Represent one turn spent moving toward a restricted zone."""

    origin: str
    destination: str


Location: TypeAlias = str | Transit
Route: TypeAlias = tuple[Location, ...]
ZoneSlot: TypeAlias = tuple[int, str]
ConnectionSlot: TypeAlias = tuple[int, str, str]


@dataclass
class RouteSchedule:
    """Store drone routes and track reserved zones and connections."""

    _routes: dict[int, Route] = field(default_factory=dict)
    _zone_usage: dict[ZoneSlot, int] = field(default_factory=dict)
    _connection_usage: dict[ConnectionSlot, int] = field(default_factory=dict)

    @property
    def last_turn(self) -> int:
        """Return the final turn occupied by any registered route."""

        return max(
            (len(route) - 1 for route in self._routes.values()), default=0
        )

    @property
    def drone_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._routes))

    def add_route(self, drone_id: int, route: Route) -> None:
        """Register a drone route and reserve all resources it uses."""

        if drone_id in self._routes:
            raise ValueError(f"Drone {drone_id} already has a route.")

        self._routes[drone_id] = route
        self._reserve_zones(route)
        self._reserve_connections(route)

    def get_route(self, drone_id: int) -> Route:
        """Return the registered route for a drone."""

        if drone_id not in self._routes:
            raise ValueError(f"Drone {drone_id} does not have a route.")

        return self._routes[drone_id]

    def can_enter_zone(self, turn: int, zone: Zone) -> bool:
        """Return whether a zone has capacity at the given turn."""

        if zone.capacity is None:
            return True

        usage = self._zone_usage.get((turn, zone.name), 0)
        return usage < zone.capacity

    def can_use_connection(self, turn: int, connection: Connection) -> bool:
        """Return whether a connection has capacity at the given turn."""

        slot = self._connection_slot(
            turn, connection.zone_a, connection.zone_b
        )

        usage = self._connection_usage.get(slot, 0)
        return usage < connection.capacity

    def _reserve_zones(self, route: Route) -> None:
        """Reserve each zone occupied by a route."""

        for turn, location in enumerate(route):
            if isinstance(location, Transit):
                continue

            slot = (turn, location)
            self._zone_usage[slot] = self._zone_usage.get(slot, 0) + 1

    def _reserve_connections(self, route: Route) -> None:
        """Reserve each connection traversed by a route."""

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
        """Return the connection used between two route locations."""

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
        """Build a direction-independent connection reservation key."""

        first, second = sorted((zone_a, zone_b))
        return turn, first, second
