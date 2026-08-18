"""Test the color helpers shared by the visualizer."""

import pytest

from fly_in.models import Zone, ZoneRole, ZoneType
from fly_in.rendering.gui.theme import (
    RGB_COLORS,
    SPEEDS,
    TURN_SECONDS,
    animation_ms,
    TYPE_COLORS,
    to_hex,
    zone_fill,
    zone_label,
)


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


@pytest.mark.parametrize(
    ("rgb", "expected"),
    [
        ((0, 0, 0), "#000000"),
        ((255, 255, 255), "#ffffff"),
        ((255, 0, 0), "#ff0000"),
        ((0, 128, 0), "#008000"),
        ((0, 0, 255), "#0000ff"),
        ((255, 165, 0), "#ffa500"),
    ],
)
def test_to_hex_keeps_the_channel_order(
    rgb: tuple[int, int, int], expected: str
) -> None:
    assert to_hex(rgb) == expected


def test_to_hex_pads_every_channel_to_two_digits() -> None:
    assert to_hex((1, 2, 3)) == "#010203"


@pytest.mark.parametrize("name", sorted(RGB_COLORS))
def test_every_named_color_converts_to_a_hex_string(name: str) -> None:
    hex_color = to_hex(RGB_COLORS[name])

    assert len(hex_color) == 7
    assert hex_color.startswith("#")
    assert int(hex_color[1:], 16) >= 0


def test_a_named_color_wins_over_the_zone_type() -> None:
    zone = make_zone("red", ZoneType.RESTRICTED)

    assert zone_fill(zone) == to_hex(RGB_COLORS["red"])


def test_an_unknown_color_falls_back_to_the_zone_type() -> None:
    zone = make_zone("rainbow", ZoneType.PRIORITY)

    assert zone_fill(zone) == TYPE_COLORS[ZoneType.PRIORITY]


def test_a_zone_without_a_color_falls_back_to_the_zone_type() -> None:
    zone = make_zone(None, ZoneType.RESTRICTED)

    assert zone_fill(zone) == TYPE_COLORS[ZoneType.RESTRICTED]


def test_every_zone_type_has_a_fallback_color() -> None:
    for zone_type in ZoneType:
        assert zone_type in TYPE_COLORS


@pytest.mark.parametrize("speed", SPEEDS)
def test_the_animation_ends_before_the_next_turn(speed: float) -> None:
    interval = TURN_SECONDS / speed

    assert animation_ms(interval) < interval * 1000.0


def test_a_shorter_turn_gives_a_shorter_animation() -> None:
    assert animation_ms(0.15) < animation_ms(0.6)


def test_a_limited_zone_shows_its_capacity() -> None:
    zone = make_zone(None)
    zone.capacity = 3

    assert zone_label(zone) == "zone ×3"


def test_a_zone_holding_one_drone_shows_no_capacity() -> None:
    zone = make_zone(None)
    zone.capacity = 1

    assert zone_label(zone) == "zone"


def test_an_unlimited_zone_shows_no_capacity() -> None:
    zone = make_zone(None)
    zone.capacity = None

    assert zone_label(zone) == "zone"
