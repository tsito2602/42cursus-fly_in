from pathlib import Path

from fly_in.models import Connection, Map, Zone, ZoneRole, ZoneType
from fly_in.rendering import render_html
from fly_in.routing import RouteSchedule, Transit


def test_writes_interactive_schedule_html(tmp_path: Path) -> None:
    map = Map(
        nb_drones=1,
        zones={
            "start": Zone(
                name="start",
                x=0,
                y=0,
                zone_role=ZoneRole.START,
                color="green",
                capacity=None,
            ),
            "restricted": Zone(
                name="restricted",
                x=1,
                y=0,
                zone_role=ZoneRole.HUB,
                zone_type=ZoneType.RESTRICTED,
                color="red",
            ),
            "goal": Zone(
                name="goal",
                x=2,
                y=0,
                zone_role=ZoneRole.END,
                color="yellow",
                capacity=None,
            ),
        },
        connections=[
            Connection(zone_a="start", zone_b="restricted"),
            Connection(zone_a="restricted", zone_b="goal"),
        ],
        start="start",
        end="goal",
    )
    schedule = RouteSchedule()
    schedule.add_route(
        1,
        (
            "start",
            Transit("start", "restricted"),
            "restricted",
            "goal",
        ),
    )
    output = tmp_path / "visualizations" / "simulation.html"

    render_html(map, schedule, str(output))

    html = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "Fly-in Route Visualizer" in html
    assert 'id="zoom"' in html
    assert 'id="fit"' in html
    assert '"color":"red"' in html
    assert '"zone_a":"start","zone_b":"restricted"' in html
    assert (
        '"kind":"transit","origin":"start",'
        '"destination":"restricted"' in html
    )
    assert "__SIMULATION_DATA__" not in html
