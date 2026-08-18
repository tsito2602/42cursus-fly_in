"""Render a route schedule as colored terminal output."""

from fly_in.routing import RouteSchedule, Transit


def render_schedule(schedule: RouteSchedule) -> None:
    """Print all drone movements grouped by simulation turn."""

    lines: list[str] = []

    for turn in range(1, schedule.last_turn + 1):
        line: list[str] = []

        for drone_id in schedule.drone_ids:
            route = schedule.get_route(drone_id)

            if len(route) <= turn:
                continue

            previous = route[turn - 1]
            current = route[turn]

            if current == previous:
                continue

            if isinstance(current, Transit):
                location = f"{current.origin}-{current.destination}"
            else:
                location = current

            line.append(f"D{drone_id}-{location}")

        lines.append(" ".join(line))

    print("\n".join(lines))
