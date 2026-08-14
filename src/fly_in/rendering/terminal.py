from fly_in.models import Map
from fly_in.routing import RouteSchedule
from fly_in.routing import Transit

ANSI_COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
}

ANSI_RESET = "\033[0m"


def render_schedule(map: Map, schedule: RouteSchedule) -> None:
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
    if color is None:
        return text

    color_code = ANSI_COLORS.get(color)

    if color_code is None:
        return text

    return f"{color_code}{text}{ANSI_RESET}"
