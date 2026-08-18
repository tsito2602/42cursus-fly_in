"""Test the zone type color key."""

import flet as ft
import flet.canvas as cv

from fly_in.models import ZoneType
from fly_in.rendering.gui.legend import ZONE_TYPES, Legend
from fly_in.rendering.gui.theme import (
    DASH_PATTERN,
    OUTLINE_WIDTH,
    TYPE_COLORS,
    outline_dashed,
)


def lines_of(legend: Legend) -> list[cv.Line]:
    """Return the sample line of every entry."""

    return [
        shape
        for entry in legend.controls
        if isinstance(entry, ft.Row)
        for control in entry.controls
        if isinstance(control, cv.Canvas)
        for shape in control.shapes
        if isinstance(shape, cv.Line)
    ]


def paints_of(legend: Legend) -> list[ft.Paint]:
    """Return the paint of every sample line."""

    return [line.paint for line in lines_of(legend)]


def captions_of(legend: Legend) -> list[str]:
    """Return the caption of every entry."""

    return [
        str(control.value)
        for entry in legend.controls
        if isinstance(entry, ft.Row)
        for control in entry.controls
        if isinstance(control, ft.Text)
    ]


def test_every_zone_type_is_listed() -> None:
    assert set(ZONE_TYPES) == set(ZoneType)
    assert len(ZONE_TYPES) == len(ZoneType)


def test_each_entry_names_its_zone_type() -> None:
    assert captions_of(Legend()) == [
        zone_type.value.capitalize() for zone_type in ZONE_TYPES
    ]


def test_each_sample_carries_the_outline_color() -> None:
    colors = [paint.color for paint in paints_of(Legend())]

    assert colors == [TYPE_COLORS[zone_type] for zone_type in ZONE_TYPES]


def test_each_sample_is_a_horizontal_line() -> None:
    for line in lines_of(Legend()):
        assert line.y1 == line.y2
        assert line.x2 > line.x1


def test_each_sample_is_as_thick_as_a_zone_outline() -> None:
    for paint in paints_of(Legend()):
        assert paint.stroke_width == OUTLINE_WIDTH


def test_only_the_dashed_zone_types_get_a_dashed_sample() -> None:
    dashed = {
        zone_type: paint.stroke_dash_pattern
        for zone_type, paint in zip(ZONE_TYPES, paints_of(Legend()))
    }

    assert dashed == {
        ZoneType.NORMAL: None,
        ZoneType.PRIORITY: None,
        ZoneType.RESTRICTED: list(DASH_PATTERN),
        ZoneType.BLOCKED: list(DASH_PATTERN),
    }


def test_the_samples_follow_the_shared_dash_rule() -> None:
    for zone_type, paint in zip(ZONE_TYPES, paints_of(Legend())):
        assert (paint.stroke_dash_pattern is not None) is outline_dashed(
            zone_type
        )
