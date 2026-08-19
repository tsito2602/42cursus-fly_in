"""Convert between the center of a shape and the corner Flet draws from."""

from typing import TypeAlias

Point: TypeAlias = tuple[float, float]


def top_left(point: Point, radius: float) -> Point:
    """Return the top-left corner of a circle centered on a point."""

    x, y = point

    return (x - radius, y - radius)
