"""Load map files and convert their contents into validated maps."""

from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from fly_in.models import Connection, Map, Zone, ZoneRole, ZoneType

from .map_builder import MapBuilder

ZONE_ROLES = {
    "start_hub": ZoneRole.START,
    "end_hub": ZoneRole.END,
    "hub": ZoneRole.HUB,
}


class ParsingError(Exception):
    """Report a failure while loading or validating a map file."""


class LineParsingError(ParsingError):
    """Report a map syntax error with its source line number."""

    def __init__(self, msg: str, line_number: int) -> None:
        """Create an error containing the line number and failure message."""

        super().__init__(f"ParsingError: Line {line_number} - {msg}")


class MapParser:
    """Parse one map file into a validated map."""

    def __init__(self, file: str) -> None:
        """Create a parser for the given map file path."""

        self._file = Path(file)

    def load(self) -> Map:
        """Load, parse, and validate the configured map file."""

        try:
            with self._file.open("rb") as lines:
                builder = self._parse_lines(lines)
                return builder.build()
        except OSError as error:
            raise ParsingError(f"Unable to read map file: {error}") from error
        except ValidationError as error:
            raise ParsingError(str(error)) from error

    def _parse_lines(self, lines: Iterable[bytes]) -> MapBuilder:
        """Parse all lines into a new map builder."""

        builder = MapBuilder()
        last_line_number = 0

        for line_number, raw_content in enumerate(lines, start=1):
            last_line_number = line_number

            try:
                field = self._parse_line(raw_content)
                if field is None:
                    continue

                key, value = field
                self._apply_field(builder, key, value)
            except ValueError as error:
                raise LineParsingError(str(error), line_number) from error

        if builder.nb_drones is None:
            raise LineParsingError(
                "The first non-comment line must define 'nb_drones'.",
                last_line_number + 1 if last_line_number else 1,
            )

        missing = [
            key
            for key in ("start_hub", "end_hub")
            if key not in builder.seen_fields
        ]
        if missing:
            label = "field" if len(missing) == 1 else "fields"
            names = ", ".join(f"'{key}'" for key in missing)
            raise LineParsingError(
                f"Missing required {label} before end of file: {names}.",
                last_line_number + 1,
            )

        return builder

    def _parse_line(self, raw_content: bytes) -> tuple[str, str] | None:
        """Parse one physical line into a key and value."""

        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Line must be valid UTF-8.") from error

        content = content.split("#", 1)[0].strip()
        if not content:
            return None

        if ":" not in content:
            raise ValueError("Expected KEY: VALUE format.")

        key, value = content.split(":", 1)
        return key.strip(), value.strip()

    def _apply_field(
        self,
        builder: MapBuilder,
        key: str,
        value: str,
    ) -> None:
        """Parse one field and apply it to the map builder."""

        self._validate_first_field(builder, key)

        match key:
            case "nb_drones":
                builder.set_nb_drones(self._parse_positive_int(value, key))
            case "start_hub" | "end_hub" | "hub":
                builder.add_zone(key, self._parse_zone(key, value))
            case "connection":
                builder.add_connection(self._parse_connection(value))
            case _:
                raise ValueError(f"Unknown key '{key}'.")

    def _validate_first_field(
        self,
        builder: MapBuilder,
        key: str,
    ) -> None:
        """Ensure that the first non-comment line defines the drone count."""

        if builder.nb_drones is None and key != "nb_drones":
            raise ValueError(
                "The first non-comment line must define 'nb_drones'."
            )

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

        return Zone(
            name=name,
            x=coordinate_x,
            y=coordinate_y,
            zone_role=ZONE_ROLES[key],
            zone_type=zone_type,
            color=metadata.get("color"),
            capacity=capacity,
        )

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

        return Connection(
            zone_a=zone_a,
            zone_b=zone_b,
            capacity=capacity,
        )

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
