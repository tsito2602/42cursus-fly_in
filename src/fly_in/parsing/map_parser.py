"""Load map files and convert their contents into validated graphs."""

from argparse import ArgumentParser
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError
from fly_in.models import Graph, Zone, ZoneRole, ZoneType, Connection

SINGLE_FIELDS = {"nb_drones", "start_hub", "end_hub"}

ZONE_ROLES = {
    "start_hub": ZoneRole.START,
    "end_hub": ZoneRole.END,
    "hub": ZoneRole.HUB,
}


@dataclass
class _ParseState:
    """Hold values and duplicate-tracking data accumulated across lines."""

    nb_drones: int | None = None
    zones: dict[str, Zone] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    start: str | None = None
    end: str | None = None
    seen_fields: set[str] = field(default_factory=set)
    seen_connections: set[frozenset[str]] = field(default_factory=set)

    def to_parsed_data(self) -> dict[str, object]:
        """Build the mapping consumed by Pydantic graph validation."""

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

        return parsed_data


class ParsingError(Exception):
    """Report a failure while loading or validating a map file."""

    pass


class LineParsingError(ParsingError):
    """Report a map syntax error with its source line number."""

    def __init__(self, msg: str, line_number: int) -> None:
        """Create an error containing the line number and failure message."""

        super().__init__(f"ParsingError: Line {line_number} - {msg}")


def get_map_file() -> str:
    """Read the map file path from the command-line arguments."""

    parser = ArgumentParser(
        prog="fly_in", description="Drones are interesting"
    )
    parser.add_argument("map", help="map file")
    args = parser.parse_args()

    return str(args.map)


class MapParser:
    """Parse one map file into a validated graph."""

    def __init__(self, file: str) -> None:
        """Create a parser for the given map file path."""

        self._file = Path(file)

    def load(self) -> Graph:
        """Load, parse, and validate the configured map file."""

        try:
            with self._file.open("rb") as lines:
                parsed_data = self._parse_lines(lines)
                return Graph.model_validate(parsed_data)
        except OSError as error:
            raise ParsingError(f"Unable to read map file: {error}") from error
        except ValidationError as error:
            raise ParsingError(str(error)) from error

    def _parse_lines(self, lines: Iterable[bytes]) -> dict[str, object]:
        """Parse all lines while preserving cross-line parsing state."""

        state = _ParseState()
        last_line_number = 0

        for line_number, raw_content in enumerate(lines, start=1):
            last_line_number = line_number

            try:
                content = raw_content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise LineParsingError(
                    "Line must be valid UTF-8.",
                    line_number,
                ) from error

            content = content.split("#", 1)[0].strip()
            if not content:
                if line_number == 1:
                    raise LineParsingError(
                        "The first line must define 'nb_drones'.",
                        line_number,
                    )
                continue

            try:
                if ":" not in content:
                    raise ValueError("Expected KEY: VALUE format.")

                key, value = content.split(":", 1)
                key = key.strip()
                value = value.strip()
                self._apply_field(state, key, value, line_number)
            except ValueError as error:
                raise LineParsingError(str(error), line_number) from error

        if last_line_number == 0:
            raise LineParsingError(
                "The first line must define 'nb_drones'.",
                1,
            )

        missing = [
            key
            for key in ("start_hub", "end_hub")
            if key not in state.seen_fields
        ]
        if missing:
            label = "field" if len(missing) == 1 else "fields"
            names = ", ".join(f"'{key}'" for key in missing)
            raise LineParsingError(
                f"Missing required {label} before end of file: {names}.",
                last_line_number + 1,
            )

        return state.to_parsed_data()

    def _apply_field(
        self,
        state: _ParseState,
        key: str,
        value: str,
        line_number: int,
    ) -> None:
        """Parse one field and apply it to the accumulated map state."""

        match key:
            case "nb_drones":
                self._mark_single_field(state, key)
                state.nb_drones = self._parse_positive_int(value, key)
            case "start_hub" | "end_hub" | "hub":
                self._validate_first_field(key, line_number)
                self._mark_single_field(state, key)
                self._add_zone(state, key, value)
            case "connection":
                self._validate_first_field(key, line_number)
                self._add_connection(state, value)
            case _:
                raise ValueError(f"Unknown key '{key}'.")

    def _validate_first_field(self, key: str, line_number: int) -> None:
        """Ensure that the first physical line defines the drone count."""

        if line_number == 1 and key != "nb_drones":
            raise ValueError("The first line must define 'nb_drones'.")

    def _mark_single_field(self, state: _ParseState, key: str) -> None:
        """Reject a repeated field that may appear only once."""

        if key not in SINGLE_FIELDS:
            return

        if key in state.seen_fields:
            raise ValueError(f"Duplicate field: '{key}'")

        state.seen_fields.add(key)

    def _add_zone(
        self,
        state: _ParseState,
        key: str,
        value: str,
    ) -> None:
        """Parse a zone and add it to the accumulated map state."""

        zone = self._parse_zone(key, value)

        if zone.name in state.zones:
            raise ValueError(f"Duplicate zone name: '{zone.name}'")

        state.zones[zone.name] = zone

        if key == "start_hub":
            state.start = zone.name
        elif key == "end_hub":
            state.end = zone.name

    def _add_connection(self, state: _ParseState, value: str) -> None:
        """Parse and add a connection after checking global constraints."""

        connection = self._parse_connection(value)
        endpoints = frozenset((connection.zone_a, connection.zone_b))
        unknown = endpoints - state.zones.keys()

        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(
                "Connection references zones that have not "
                f"been defined: {names}"
            )

        if endpoints in state.seen_connections:
            raise ValueError(
                "Duplicate connection: "
                f"{connection.zone_a}-{connection.zone_b}"
            )

        state.seen_connections.add(endpoints)
        state.connections.append(connection)

    def _parse_positive_int(self, value: str, field: str) -> int:
        """Parse a field value as an integer greater than zero."""

        try:
            number = int(value)
        except ValueError as error:
            raise ValueError(f'"{field}" must be an integer.') from error

        if number < 1:
            raise ValueError(f'"{field}" must be a positive integer.')

        return number

    def _parse_zone(self, key: str, value: str) -> Zone:
        """Parse one zone field, including its optional metadata."""

        data_str, metadata_str = self._split_metadata_suffix(value)

        data = data_str.split()
        if len(data) != 3:
            raise ValueError(
                "Zone must have a name and a coordinate: NAME X Y"
            )
        name, x, y = data

        if "-" in name:
            raise ValueError("Zone names must not contain '-'.")

        metadata = self._parse_metadata(metadata_str)

        allowed_metadata = {"zone", "color", "max_drones"}
        unknown_metadata = metadata.keys() - allowed_metadata
        if unknown_metadata:
            unknown = ", ".join(sorted(unknown_metadata))
            raise ValueError(f"Unknown zone metadata: {unknown}")

        capacity = None
        if key == "hub":
            capacity = self._parse_positive_int(
                metadata.get("max_drones", "1"), "max_drones"
            )

        try:
            coordinate_x = int(x)
            coordinate_y = int(y)
        except ValueError as error:
            raise ValueError("Zone coordinates must be integers.") from error

        zone_type_value = metadata.get("zone", ZoneType.NORMAL)
        try:
            zone_type = ZoneType(zone_type_value)
        except ValueError as error:
            raise ValueError(
                f"Invalid zone type '{zone_type_value}'. Expected one of: "
                "normal, blocked, restricted, priority."
            ) from error

        try:
            return Zone(
                name=name,
                x=coordinate_x,
                y=coordinate_y,
                zone_role=ZONE_ROLES[key],
                zone_type=zone_type,
                color=metadata.get("color"),
                capacity=capacity,
            )
        except (ValueError, ValidationError) as error:
            raise ValueError(str(error)) from error

    def _parse_connection(self, value: str) -> Connection:
        """Parse one connection field, including its optional capacity."""

        data_str, metadata_str = self._split_metadata_suffix(value)

        data = data_str.split("-")
        if len(data) != 2:
            raise ValueError("Connection must have two zones: <name1>-<name2>")

        zone_a, zone_b = (zone.strip() for zone in data)

        if not zone_a or not zone_b:
            raise ValueError("Connection endpoint names must not be empty.")

        metadata = self._parse_metadata(metadata_str)

        allowed_metadata = {"max_link_capacity"}
        unknown_metadata = metadata.keys() - allowed_metadata
        if unknown_metadata:
            unknown = ", ".join(sorted(unknown_metadata))
            raise ValueError(f"Unknown connection metadata: {unknown}")

        capacity = self._parse_positive_int(
            metadata.get("max_link_capacity", "1"),
            "max_link_capacity",
        )

        if zone_a == zone_b:
            raise ValueError("Connection endpoints must be different.")

        try:
            return Connection(
                zone_a=zone_a,
                zone_b=zone_b,
                capacity=capacity,
            )
        except (ValueError, ValidationError) as error:
            raise ValueError(str(error)) from error

    def _split_metadata_suffix(self, value: str) -> tuple[str, str | None]:
        """Separate a field's main value from bracketed metadata."""

        if "[" not in value and "]" not in value:
            return value, None

        if (
            value.count("[") != 1
            or value.count("]") != 1
            or not value.endswith("]")
        ):
            raise ValueError(
                "Metadata must be enclosed in a "
                "single pair of square brackets: [...]"
            )

        data_str, metadata_with_bracket = value.split("[", 1)

        return (data_str.strip(), metadata_with_bracket[:-1].strip())

    def _parse_metadata(self, metadata_str: str | None) -> dict[str, str]:
        """Parse whitespace-separated KEY=VALUE metadata entries."""

        if metadata_str is None or not metadata_str:
            return {}

        metadata: dict[str, str] = {}

        for item in metadata_str.split():
            if item.count("=") != 1:
                raise ValueError("Metadata must use the KEY=VALUE format.")

            key, value = item.split("=", 1)

            if key in metadata:
                raise ValueError(f"Duplicate metadata key: '{key}'")

            metadata[key] = value

        return metadata
