"""Accumulate parsed map values and enforce map-wide constraints."""

from dataclasses import dataclass, field

from fly_in.models import Connection, Map, Zone

SINGLE_FIELDS = {"nb_drones", "start_hub", "end_hub"}


@dataclass
class MapBuilder:
    """Accumulate parsed values and build a validated map."""

    nb_drones: int | None = None
    zones: dict[str, Zone] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    start: str | None = None
    end: str | None = None
    seen_fields: set[str] = field(default_factory=set)
    seen_connections: set[frozenset[str]] = field(default_factory=set)

    def set_nb_drones(self, value: int) -> None:
        """Set the drone count after checking for a duplicate field."""

        self._mark_single_field("nb_drones")
        self.nb_drones = value

    def add_zone(self, key: str, zone: Zone) -> None:
        """Add a zone and update the start or end reference if needed."""

        self._mark_single_field(key)

        if zone.name in self.zones:
            raise ValueError(f"Duplicate zone name: '{zone.name}'")

        self.zones[zone.name] = zone

        if key == "start_hub":
            self.start = zone.name
        elif key == "end_hub":
            self.end = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Add a connection after checking map-wide constraints."""

        endpoints = frozenset((connection.zone_a, connection.zone_b))
        unknown = endpoints - self.zones.keys()

        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(
                "Connection references zones that have not "
                f"been defined: {names}"
            )

        if endpoints in self.seen_connections:
            raise ValueError(
                "Duplicate connection: "
                f"{connection.zone_a}-{connection.zone_b}"
            )

        self.seen_connections.add(endpoints)
        self.connections.append(connection)

    def _mark_single_field(self, key: str) -> None:
        """Reject a repeated field that may appear only once."""

        if key not in SINGLE_FIELDS:
            return

        if key in self.seen_fields:
            raise ValueError(f"Duplicate field: '{key}'")

        self.seen_fields.add(key)

    def build(self) -> Map:
        """Build and validate a map from the accumulated values."""

        parsed_data: dict[str, object] = {
            "zones": self.zones,
            "connections": self.connections,
        }

        if self.nb_drones is not None:
            parsed_data["nb_drones"] = self.nb_drones
        if self.start is not None:
            parsed_data["start"] = self.start
        if self.end is not None:
            parsed_data["end"] = self.end

        return Map.model_validate(parsed_data)
