"""Route planning functionality."""

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import TypeAlias
from fly_in.models import Map
from fly_in.models import ZoneType
from .route_schedule import Location, Route, RouteSchedule, Transit


@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str


CameFrom: TypeAlias = dict[_SearchState, _SearchState | None]


class RoutePlanner:
    def __init__(self, map: Map, schedule: RouteSchedule):
        self._map = map
        self._schedule = schedule
        self._min_turns_to_goal: dict[str, int] = (
            self._calc_min_turns_to_goal()
        )

    def find_route(self) -> Route | None:
        start = _SearchState(turn=0, zone_name=self._map.start)

        if start.zone_name not in self._min_turns_to_goal:
            return None

        candidates = [start]
        came_from: CameFrom = {start: None}

        while candidates:
            current = min(
                candidates,
                key=lambda state: (state.turn + self._heuristic(state)),
            )
            candidates.remove(current)

            if current.zone_name == self._map.end:
                return self._construct_route(came_from, current)

            for next_state in self._next_states(current):
                if next_state in came_from:
                    continue

                if next_state.zone_name not in self._min_turns_to_goal:
                    continue

                came_from[next_state] = current
                candidates.append(next_state)

        return None

    def _construct_route(
        self, came_from: CameFrom, goal: _SearchState
    ) -> Route:
        states: list[_SearchState] = []
        current: _SearchState | None = goal

        while current is not None:
            states.append(current)
            current = came_from[current]

        states.reverse()

        locations: list[Location] = [states[0].zone_name]

        for index in range(1, len(states)):
            previous = states[index - 1]
            current = states[index]

            if current.turn - previous.turn == 2:
                locations.append(
                    Transit(
                        origin=previous.zone_name,
                        destination=current.zone_name,
                    )
                )

            locations.append(current.zone_name)

        return tuple(locations)

    def _next_states(self, current: _SearchState) -> list[_SearchState]:
        next_states: list[_SearchState] = []

        for connection in self._map.connections:
            if current.zone_name == connection.zone_a:
                destination_name = connection.zone_b
            elif current.zone_name == connection.zone_b:
                destination_name = connection.zone_a
            else:
                continue

            destination = self._map.zones[destination_name]

            if destination.zone_type is ZoneType.BLOCKED:
                continue

            arrival_turn = current.turn + self._movement_turns(
                destination_name
            )

            if not all(
                self._schedule.can_use_connection(turn, connection)
                for turn in range(current.turn, arrival_turn)
            ):
                continue

            if not self._schedule.can_enter_zone(arrival_turn, destination):
                continue

            next_states.append(_SearchState(arrival_turn, destination_name))

        wait_turn = current.turn + 1
        current_zone = self._map.zones[current.zone_name]

        if self._schedule.can_enter_zone(wait_turn, current_zone):
            next_states.append(_SearchState(wait_turn, current.zone_name))

        return next_states

    def _heuristic(self, state: _SearchState) -> int:
        return self._min_turns_to_goal[state.zone_name]

    def _calc_min_turns_to_goal(self) -> dict[str, int]:
        min_turns = {self._map.end: 0}
        candidates = [(0, self._map.end)]

        while candidates:
            turns, current_zone_name = heappop(candidates)

            if turns != min_turns[current_zone_name]:
                continue

            for connection in self._map.connections:
                if current_zone_name == connection.zone_a:
                    neighbor_zone_name = connection.zone_b
                elif current_zone_name == connection.zone_b:
                    neighbor_zone_name = connection.zone_a
                else:
                    continue

                current_zone = self._map.zones[current_zone_name]
                neighbor_zone = self._map.zones[neighbor_zone_name]

                if (
                    current_zone.zone_type is ZoneType.BLOCKED
                    or neighbor_zone.zone_type is ZoneType.BLOCKED
                ):
                    continue

                new_turns = turns + self._movement_turns(neighbor_zone_name)
                known_turns = min_turns.get(neighbor_zone_name)
                if known_turns is not None and known_turns <= new_turns:
                    continue

                min_turns[neighbor_zone_name] = new_turns
                heappush(candidates, (new_turns, neighbor_zone_name))

        return min_turns

    def _movement_turns(self, destination_name: str) -> int:
        destination = self._map.zones[destination_name]
        if destination.zone_type is ZoneType.RESTRICTED:
            return 2

        return 1
