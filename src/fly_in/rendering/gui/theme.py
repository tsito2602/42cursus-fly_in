"""Define the colors and dimensions shared by the visualizer."""

from typing import TypeAlias

from fly_in.models import Connection, Zone, ZoneRole, ZoneType

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 700
CHROME_HEIGHT = 140
MIN_CANVAS_WIDTH = 400
MIN_CANVAS_HEIGHT = 300

TURN_SECONDS = 0.6
SPEEDS = (0.5, 1.0, 2.0, 4.0)

RING_SLOTS = 6
CROWD_THRESHOLD = RING_SLOTS + 1

BACKGROUND = "#12161c"
LINE = "#4a5568"
LABEL = "#cbd5e0"
DRONE = "#ffffff"
DRONE_OUTLINE = "#555666"

TYPE_COLORS = {
    ZoneType.NORMAL: "#94a3b8",
    ZoneType.PRIORITY: "#38bdf8",
    ZoneType.RESTRICTED: "#f59e0b",
    ZoneType.BLOCKED: "#475569",
}

DASHED_TYPES = (ZoneType.RESTRICTED, ZoneType.BLOCKED)
OUTLINE_WIDTH = 3.0
DASH_PATTERN = (6.0, 4.0)

LINK_HOVER_THICKNESS = 12.0

ROLE_LABELS = {
    ZoneRole.START: "START",
    ZoneRole.END: "GOAL",
}

ROLE_RADIUS = 1.35

ROLE_COLORS = {
    ZoneRole.START: "#4ade80",  # green
    ZoneRole.END: "#facc15",  # yellow
}

RAINBOW = "rainbow"
RAINBOW_COLORS = (
    "#ff0000",  # red
    "#ff7f00",  # orange
    "#ffff00",  # yellow
    "#00ff00",  # green
    "#0000ff",  # blue
    "#8b00ff",  # violet
    "#ff0000",  # back to red, so the sweep has no seam
)

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


def is_rainbow(zone: Zone) -> bool:
    """Tell whether a zone asks for the rainbow gradient."""

    return zone.color == RAINBOW


def zone_fill(zone: Zone) -> str:
    """Return the fill color of a zone."""

    rgb = RGB_COLORS.get(zone.color or "")

    if rgb is None:
        return TYPE_COLORS[zone.zone_type]

    return to_hex(rgb)


def outline_dashed(zone_type: ZoneType) -> bool:
    """Tell whether a zone type is drawn with a dashed outline."""

    return zone_type in DASHED_TYPES


def zone_details(zone: Zone) -> str:
    """Return the lines describing a zone on its tooltip."""

    capacity = "unlimited" if zone.capacity is None else zone.capacity
    lines = [
        f"name: {zone.name}",
        f"type: {zone.zone_type.value}",
        f"capacity: {capacity}",
        f"position: ({zone.x}, {zone.y})",
    ]

    if zone.zone_role is not ZoneRole.HUB:
        lines.insert(1, f"role: {zone.zone_role.value}")

    if zone.color is not None:
        lines.append(f"color: {zone.color}")

    return "\n".join(lines)


def connection_details(connection: Connection) -> str:
    """Return the lines describing a connection on its tooltip."""

    return "\n".join(
        [
            f"zones: {connection.zone_a} - {connection.zone_b}",
            f"capacity: {connection.capacity}",
        ]
    )


def zone_radius(scale: float) -> float:
    """Return the drawing radius of a zone circle."""

    return min(scale * 0.22, 26.0)


def drawn_radius(zone: Zone, scale: float) -> float:
    """Return the radius of a zone, the start and the end being larger."""

    if zone.zone_role is ZoneRole.HUB:
        return zone_radius(scale)

    return zone_radius(scale) * ROLE_RADIUS


def label_size(scale: float) -> float:
    """Return the font size of a zone label."""

    return max(9.0, min(scale * 0.16, 14.0))


def drone_radius(scale: float) -> float:
    """Return the drawing radius of a drone marker."""

    return max(3.0, zone_radius(scale) * 0.35)


def outline_width(radius: float) -> float:
    """Return the outline thickness of a white marker."""

    return max(1.0, radius * 0.3)


def crowd_radius(scale: float) -> float:
    """Return the drawing radius of a crowd badge."""

    return zone_radius(scale) * 0.85


def crowd_font(scale: float) -> float:
    """Return the font size of a crowd count."""

    return crowd_radius(scale) * 0.9


def animation_ms(interval: float) -> int:
    """Return an animation length that fits inside one turn."""

    return int(interval * 800)
