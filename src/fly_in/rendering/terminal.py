from fly_in.routing import RouteSchedule
from fly_in.routing import Transit


def render_schedule(schedule: RouteSchedule, nb_drones: int) -> None:
    lines: list[str] = []

    for turn in range(1, schedule.last_turn + 1):
        line: list[str] = []

        for drone_id in range(1, nb_drones + 1):
            route = schedule.get_route(drone_id)

            if len(route) <= turn:
                continue

            previous = route[turn - 1]
            current = route[turn]

            if current == previous:
                continue

            if isinstance(current, Transit):
                destination = f"{current.origin}-{current.destination}"
            else:
                destination = current

            line.append(f"D{drone_id}-{destination}")

        lines.append(" ".join(line))

    print("\n".join(lines))
