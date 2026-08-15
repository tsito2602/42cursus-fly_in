import sys
from pathlib import Path

import pytest

from fly_in.main import main


def test_main_writes_requested_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    map_file = tmp_path / "map.txt"
    map_file.write_text(
        "\n".join(
            (
                "nb_drones: 1",
                "start_hub: start 0 0 [color=green]",
                "end_hub: goal 1 0 [color=yellow]",
                "connection: start-goal",
            )
        ),
        encoding="utf-8",
    )
    html_file = tmp_path / "simulation.html"
    monkeypatch.setattr(
        sys,
        "argv",
        ["fly-in", str(map_file), "--html", str(html_file)],
    )

    main()

    assert capsys.readouterr().out == "D1-\033[33mgoal\033[0m\n"
    assert html_file.is_file()
    assert "Fly-in Route Visualizer" in html_file.read_text(
        encoding="utf-8"
    )
