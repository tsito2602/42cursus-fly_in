from pathlib import Path

import pytest
from pydantic import ValidationError

from fly_in.models import Graph, Zone, ZoneRole, ZoneType
from fly_in.parsing.map_parser import LineParsingError, MapParser, ParsingError


def load_map(tmp_path: Path, content: str) -> Graph:
    map_file = tmp_path / "map.txt"
    map_file.write_text(content, encoding="utf-8")
    return MapParser(str(map_file)).load()


def test_loads_valid_map(tmp_path: Path) -> None:
    graph = load_map(
        tmp_path,
        """nb_drones: 3
start_hub: start 0 0 [zone=priority color=red]
hub: middle 1 2 [zone=restricted color=blue max_drones=2]
end_hub: end 3 4
connection: start-middle [max_link_capacity=2]
connection: middle-end
""",
    )

    assert graph.nb_drones == 3
    assert graph.start == "start"
    assert graph.end == "end"
    assert graph.zones["start"].zone_role is ZoneRole.START
    assert graph.zones["start"].zone_type is ZoneType.PRIORITY
    assert graph.zones["middle"].capacity == 2
    assert graph.connections[0].capacity == 2
    assert graph.connections[1].capacity == 1


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            "",
            "Line 1 - The first line must define 'nb_drones'.",
        ),
        (
            "# comment\nnb_drones: 1\n",
            "Line 1 - The first line must define 'nb_drones'.",
        ),
        (
            "hub: a 0 0\n",
            "Line 1 - The first line must define 'nb_drones'.",
        ),
        (
            "nb_drones: one\n",
            'Line 1 - "nb_drones" must be an integer.',
        ),
        (
            "nb_drones: 1\nunknown: value\n",
            "Line 2 - Unknown key 'unknown'.",
        ),
        (
            "nb_drones: 1\nnb_drones: 2\n",
            "Line 2 - Duplicate field: 'nb_drones'",
        ),
        (
            "nb_drones: 1\nhub: a 0 0\nhub: a 1 1\n",
            "Line 3 - Duplicate zone name: 'a'",
        ),
        (
            "nb_drones: 1\nconnection: a-b\n",
            "Line 2 - Connection references zones that have not been "
            "defined: a, b",
        ),
        (
            """nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
connection: a-b
connection: b-a
""",
            "Line 5 - Duplicate connection: b-a",
        ),
        (
            "nb_drones: 1\nhub: a 0 0 [color=red\n",
            "Line 2 - Metadata must be enclosed in a single pair of "
            "square brackets: [...]",
        ),
        (
            "nb_drones: 1\nhub: a 0 0 [color=red color=blue]\n",
            "Line 2 - Duplicate metadata key: 'color'",
        ),
        (
            "nb_drones: 1\nhub: a 0 0 [unknown=value]\n",
            "Line 2 - Unknown zone metadata: unknown",
        ),
        (
            "nb_drones: 1\nhub: a x 0\n",
            "Line 2 - Zone coordinates must be integers.",
        ),
        (
            "nb_drones: 1\nhub: a 0 0 [zone=danger]\n",
            "Line 2 - Invalid zone type 'danger'. Expected one of: "
            "normal, blocked, restricted, priority.",
        ),
        (
            """nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
connection: a-a
""",
            "Line 4 - Connection endpoints must be different.",
        ),
        (
            "nb_drones: 1\n",
            "Line 2 - Missing required fields before end of file: "
            "'start_hub', 'end_hub'.",
        ),
        (
            "nb_drones: 1\nstart_hub: start 0 0\n",
            "Line 3 - Missing required field before end of file: "
            "'end_hub'.",
        ),
        (
            "nb_drones: 1\nend_hub: end 0 0\n",
            "Line 3 - Missing required field before end of file: "
            "'start_hub'.",
        ),
    ],
)
def test_reports_line_parsing_errors(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    with pytest.raises(LineParsingError, match=None) as error:
        load_map(tmp_path, content)

    assert str(error.value) == f"ParsingError: {message}"


def test_reports_invalid_utf8_line(tmp_path: Path) -> None:
    map_file = tmp_path / "map.txt"
    map_file.write_bytes(b"nb_drones: 1\n\xff\n")

    with pytest.raises(LineParsingError, match=None) as error:
        MapParser(str(map_file)).load()

    assert str(error.value) == (
        "ParsingError: Line 2 - Line must be valid UTF-8."
    )


def test_wraps_file_errors(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.txt"

    with pytest.raises(ParsingError, match=None) as error:
        MapParser(str(missing_file)).load()

    assert str(error.value).startswith("Unable to read map file: ")


def test_graph_validates_references_without_connections() -> None:
    end = Zone(
        name="end",
        x=0,
        y=0,
        zone_role=ZoneRole.END,
        color=None,
    )

    with pytest.raises(ValidationError, match="Unknown start zone: 'start'"):
        Graph(
            nb_drones=1,
            zones={end.name: end},
            connections=[],
            start="start",
            end=end.name,
        )
