"""Define and validate a drone network map."""

from pydantic import BaseModel, Field, model_validator
from .zone import Zone
from .connection import Connection


class Map(BaseModel):
    """Represent the zones, connections, and fleet of one simulation."""

    nb_drones: int = Field(ge=1)
    zones: dict[str, Zone]
    connections: list[Connection]
    start: str
    end: str

    @model_validator(mode="after")
    def validate_references(self) -> "Map":
        """Ensure the start and end names refer to defined zones."""

        zone_names = set(self.zones)

        if self.start not in zone_names:
            raise ValueError(f"Unknown start zone: '{self.start}'")

        if self.end not in zone_names:
            raise ValueError(f"Unknown end zone: '{self.end}'")

        return self

    @model_validator(mode="after")
    def validate_connections(self) -> "Map":
        """Ensure connections reference known zones without duplicates."""

        zone_names = set(self.zones)
        seen: set[frozenset[str]] = set()

        for connection in self.connections:
            endpoints = frozenset((connection.zone_a, connection.zone_b))

            unknown = endpoints - zone_names
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(
                    f"Connection references unknown zones: {names}"
                )

            if endpoints in seen:
                raise ValueError(
                    f"Duplicate connection: "
                    f"{connection.zone_a}-{connection.zone_b}"
                )

            seen.add(endpoints)

        return self
