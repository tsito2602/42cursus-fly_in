from argparse import ArgumentParser

from fly_in.parsing import MapParser, ParsingError
from fly_in.rendering import render_schedule
from fly_in.routing import RoutePlanner


def get_map_file() -> str:
    """Read the map file path from the command-line arguments."""

    parser = ArgumentParser(
        prog="fly-in", description="Drones are interesting"
    )
    parser.add_argument("map", help="map file")
    args = parser.parse_args()

    return str(args.map)


def main() -> None:
    file = get_map_file()
    map_parser = MapParser(file)

    try:
        map = map_parser.load()
        route_schedule = RoutePlanner(map).plan_routes()

        if route_schedule is None:
            print("No valid route from start to end.")
            return

        render_schedule(route_schedule, map.nb_drones)
    except ParsingError as error:
        print(error)


if __name__ == "__main__":
    main()
