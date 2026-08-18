"""Define the colors and dimensions shared by the visualizer."""

from typing import TypeAlias

from fly_in.models import Zone, ZoneRole, ZoneType

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 700
CHROME_HEIGHT = 140
MIN_CANVAS_WIDTH = 400
MIN_CANVAS_HEIGHT = 300

TURN_SECONDS = 0.6
SPEEDS = (0.5, 1.0, 2.0, 4.0)

RING_SLOTS = 6
CROWD_THRESHOLD = RING_SLOTS + 2

BACKGROUND = "#12161c"
LINE = "#4a5568"
LABEL = "#cbd5e0"
DRONE = "#ffffff"

TYPE_COLORS = {
    ZoneType.NORMAL: "#94a3b8",  # grey
    ZoneType.PRIORITY: "#38bdf8",  # light blue
    ZoneType.RESTRICTED: "#f59e0b",  # orange
    ZoneType.BLOCKED: "#475569",  # dark grey
}

DASHED_TYPES = (ZoneType.RESTRICTED, ZoneType.BLOCKED)
OUTLINE_WIDTH = 3.0
DASH_PATTERN = (6.0, 4.0)

ROLE_LABELS = {
    ZoneRole.START: "START",
    ZoneRole.END: "GOAL",
}

ROLE_COLORS = {
    ZoneRole.START: "#4ade80",  # green
    ZoneRole.END: "#facc15",  # yellow
}

RGB: TypeAlias = tuple[int, int, int]

RGB_COLORS: dict[str, RGB] = {
    "black": (0, 0, 0),
    "blue": (0, 0, 255),
    "brown": (165, 42, 42),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkred": (139, 0, 0),
    "gold": (255, 215, 0),
    "green": (0, 128, 0),
    "lime": (0, 255, 0),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "red": (255, 0, 0),
    "violet": (238, 130, 238),
    "yellow": (255, 255, 0),
}


def to_hex(rgb: RGB) -> str:
    """Return the ``#rrggbb`` form of an RGB triple."""

    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def zone_fill(zone: Zone) -> str:
    """Return the fill color of a zone."""

    rgb = RGB_COLORS.get(zone.color or "")

    if rgb is None:
        return TYPE_COLORS[zone.zone_type]

    return to_hex(rgb)


def outline_dashed(zone_type: ZoneType) -> bool:
    """Tell whether a zone type is drawn with a dashed outline."""

    return zone_type in DASHED_TYPES


def zone_label(zone: Zone) -> str:
    """Return the zone name, with its capacity when it is limited."""

    if zone.capacity is None or zone.capacity == 1:
        return zone.name

    return f"{zone.name} ×{zone.capacity}"


def zone_radius(scale: float) -> float:
    """Return the drawing radius of a zone circle."""

    return min(scale * 0.22, 26.0)


def label_size(scale: float) -> float:
    """Return the font size of a zone label."""

    return max(9.0, min(scale * 0.16, 14.0))


def drone_radius(scale: float) -> float:
    """Return the drawing radius of a drone marker."""

    return max(3.0, zone_radius(scale) * 0.35)


def crowd_radius(scale: float) -> float:
    """Return the drawing radius of a crowd badge."""

    return zone_radius(scale) * 0.85


def crowd_font(scale: float) -> float:
    """Return the font size of a crowd count."""

    return crowd_radius(scale) * 0.9


def animation_ms(interval: float) -> int:
    """Return an animation length that fits inside one turn."""

    return int(interval * 800)
