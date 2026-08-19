from pathlib import Path

import pytest

from fly_in.models import Zone, ZoneRole
from fly_in.parsing import MapParser
from fly_in.rendering.gui.transform import (
    MARGIN,
    MAX_SCALE,
    ViewTransform,
)

WIDTH = 1200
HEIGHT = 800

MAP_FILES = sorted(Path("maps").glob("*/*.txt"))


def make_zone(x: int, y: int) -> Zone:
    return Zone(
        name=f"z{x}_{y}",
        x=x,
        y=y,
        zone_role=ZoneRole.HUB,
        color=None,
    )


def make_transform(
    points: list[tuple[int, int]],
    width: int = WIDTH,
    height: int = HEIGHT,
) -> ViewTransform:
    return ViewTransform(
        [make_zone(x, y) for x, y in points], width, height
    )


def test_scale_is_limited_by_the_tighter_axis() -> None:
    transform = make_transform([(0, 0), (100, 1)])

    assert transform.scale == pytest.approx((WIDTH - 2 * MARGIN) / 100)


def test_a_flat_map_does_not_divide_by_zero() -> None:
    transform = make_transform([(0, 0), (1, 0), (2, 0), (3, 0)])

    assert transform.scale == MAX_SCALE


def test_a_single_zone_map_does_not_divide_by_zero() -> None:
    transform = make_transform([(4, 7)])

    assert transform.scale == MAX_SCALE
    assert transform.to_pixel(4, 7) == (WIDTH / 2, HEIGHT / 2)


def test_scale_never_exceeds_the_upper_bound() -> None:
    transform = make_transform([(0, 0), (1, 1)])

    assert transform.scale == MAX_SCALE


def test_the_y_axis_is_flipped() -> None:
    transform = make_transform([(0, -1), (0, 2)])

    _, top = transform.to_pixel(0, 2)
    _, bottom = transform.to_pixel(0, -1)

    assert top < bottom


def test_both_axes_share_one_scale() -> None:
    transform = make_transform([(0, 0), (10, 4)])

    origin_x, origin_y = transform.to_pixel(0, 0)
    moved_x, _ = transform.to_pixel(1, 0)
    _, moved_y = transform.to_pixel(0, 1)

    assert moved_x - origin_x == pytest.approx(origin_y - moved_y)


def test_the_map_is_centered_on_the_canvas() -> None:
    transform = make_transform([(2, -1), (9, 5)])

    left, bottom = transform.to_pixel(2, -1)
    right, top = transform.to_pixel(9, 5)

    assert (left + right) / 2 == pytest.approx(WIDTH / 2)
    assert (top + bottom) / 2 == pytest.approx(HEIGHT / 2)


def test_scaling_is_linear_in_map_distance() -> None:
    transform = make_transform([(0, 0), (10, 4)])

    near, _ = transform.to_pixel(1, 0)
    far, _ = transform.to_pixel(3, 0)
    origin, _ = transform.to_pixel(0, 0)

    assert far - origin == pytest.approx(3 * (near - origin))


def test_a_generator_of_zones_is_accepted() -> None:
    zones = (make_zone(x, 0) for x in range(4))

    assert ViewTransform(zones, WIDTH, HEIGHT).scale == MAX_SCALE


@pytest.mark.parametrize("path", MAP_FILES, ids=lambda p: p.stem)
def test_every_shipped_map_fits_inside_the_canvas(path: Path) -> None:
    map = MapParser(str(path)).load()
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    for zone in map.zones.values():
        pixel_x, pixel_y = transform.to_pixel(zone.x, zone.y)

        assert 0 <= pixel_x <= WIDTH
        assert 0 <= pixel_y <= HEIGHT


@pytest.mark.parametrize("path", MAP_FILES, ids=lambda p: p.stem)
def test_every_shipped_map_keeps_a_usable_scale(path: Path) -> None:
    map = MapParser(str(path)).load()
    transform = ViewTransform(map.zones.values(), WIDTH, HEIGHT)

    assert 0 < transform.scale <= MAX_SCALE
