"""Test the panels shown while the pointer rests on a shape."""

from fly_in.models import Connection, Zone, ZoneRole, ZoneType
from fly_in.rendering.gui.tooltips import connection_details, zone_details


def make_zone(
    color: str | None,
    zone_type: ZoneType = ZoneType.NORMAL,
) -> Zone:
    return Zone(
        name="zone",
        x=0,
        y=0,
        zone_role=ZoneRole.HUB,
        zone_type=zone_type,
        color=color,
    )


def test_the_details_open_with_the_zone_name() -> None:
    zone = make_zone(None)

    assert zone_details(zone).splitlines()[0] == "name: zone"


def test_the_details_carry_the_type_and_the_position() -> None:
    zone = make_zone(None, ZoneType.PRIORITY)
    zone.x, zone.y = 4, 7

    assert "type: priority" in zone_details(zone).splitlines()
    assert "position: (4, 7)" in zone_details(zone).splitlines()


def test_the_details_spell_out_a_limited_capacity() -> None:
    zone = make_zone(None)
    zone.capacity = 3

    assert "capacity: 3" in zone_details(zone).splitlines()


def test_the_details_name_an_unlimited_capacity() -> None:
    zone = make_zone(None)
    zone.capacity = None

    assert "capacity: unlimited" in zone_details(zone).splitlines()


def test_the_details_of_a_hub_carry_no_role() -> None:
    zone = make_zone(None)

    assert not any(
        line.startswith("role:")
        for line in zone_details(zone).splitlines()
    )


def test_the_details_of_the_start_carry_its_role() -> None:
    zone = make_zone(None)
    zone.zone_role = ZoneRole.START

    assert "role: start" in zone_details(zone).splitlines()


def test_the_details_carry_a_named_color() -> None:
    zone = make_zone("cyan")

    assert "color: cyan" in zone_details(zone).splitlines()


def test_the_details_of_a_plain_zone_carry_no_color() -> None:
    zone = make_zone(None)

    assert not any(
        line.startswith("color:")
        for line in zone_details(zone).splitlines()
    )


def test_the_details_name_both_ends_and_the_capacity() -> None:
    connection = Connection(zone_a="start", zone_b="middle", capacity=3)

    assert connection_details(connection) == (
        "zones: start - middle\ncapacity: 3"
    )


def test_the_details_show_no_direction() -> None:
    connection = Connection(zone_a="start", zone_b="middle")
    details = connection_details(connection).lower()

    assert "from" not in details
    assert "to:" not in details
