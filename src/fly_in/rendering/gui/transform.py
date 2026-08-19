from collections.abc import Iterable
import math

from fly_in.models import Zone

MARGIN = 60.0
MAX_SCALE = 120.0


class ViewTransform:
    """Fit map coordinates into a canvas, preserving the aspect ratio."""

    def __init__(
        self, zones: Iterable[Zone], width: int, height: int
    ) -> None:
        points = [(zone.x, zone.y) for zone in zones]

        self._min_x = min(x for x, _ in points)
        self._max_y = max(y for _, y in points)
        span_x = max(x for x, _ in points) - self._min_x
        span_y = self._max_y - min(y for _, y in points)

        self._scale = min(
            self._fit(width, span_x), self._fit(height, span_y), MAX_SCALE
        )
        self._offset_x = (width - span_x * self._scale) / 2
        self._offset_y = (height - span_y * self._scale) / 2

    @property
    def scale(self) -> float:
        """Return the pixels drawn per unit of map distance."""

        return self._scale

    def to_pixel(self, x: int, y: int) -> tuple[float, float]:
        """Convert map coordinates to pixels, flipping the y axis."""

        return (
            self._offset_x + (x - self._min_x) * self._scale,
            self._offset_y + (self._max_y - y) * self._scale,
        )

    @staticmethod
    def _fit(available: int, span: int) -> float:
        """Return the scale fitting one axis, or infinity when flat."""

        if span == 0:
            return math.inf

        return (available - 2 * MARGIN) / span
