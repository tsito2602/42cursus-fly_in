"""Render a route schedule as colored terminal output."""

from itertools import cycle

from fly_in.models import Map
from fly_in.routing import RouteSchedule
from fly_in.routing import Transit

RGB_COLORS = {
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

RAINBOW_RGB = (
    (255, 0, 0),
    (255, 165, 0),
    (255, 255, 0),
    (0, 128, 0),
    (0, 0, 255),
    (75, 0, 130),
    (238, 130, 238),
)
ANSI_RESET = "\033[0m"


def render_schedule(map: Map, schedule: RouteSchedule) -> None:
    """Print all drone movements grouped by simulation turn."""

    lines: list[str] = []

    for turn in range(1, schedule.last_turn + 1):
        line: list[str] = []

        for drone_id in range(1, map.nb_drones + 1):
            route = schedule.get_route(drone_id)

            if len(route) <= turn:
                continue

            previous = route[turn - 1]
            current = route[turn]

            if current == previous:
                continue

            if isinstance(current, Transit):
                origin = map.zones[current.origin]
                destination = map.zones[current.destination]
                location = (
                    f"{_colorize(current.origin, origin.color)}-"
                    f"{_colorize(current.destination, destination.color)}"
                )
            else:
                zone = map.zones[current]
                location = _colorize(current, zone.color)

            line.append(f"D{drone_id}-{location}")

        lines.append(" ".join(line))

    print("\n".join(lines))


def _colorize(text: str, color: str | None) -> str:
    """Apply a supported RGB terminal color to the given text."""

    if color is None:
        return text

    if color == "rainbow":
        colored_characters = (
            f"{_rgb_escape(rgb)}{character}"
            for character, rgb in zip(text, cycle(RAINBOW_RGB))
        )
        return "".join(colored_characters) + ANSI_RESET

    rgb = RGB_COLORS.get(color)

    if rgb is None:
        return text

    return f"{_rgb_escape(rgb)}{text}{ANSI_RESET}"


def _rgb_escape(rgb: tuple[int, int, int]) -> str:
    """Return an ANSI true-color escape sequence for an RGB value."""

    red, green, blue = rgb
    return f"\033[38;2;{red};{green};{blue}m"
