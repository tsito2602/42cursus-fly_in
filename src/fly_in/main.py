"""Provide the Fly-in command-line entry point."""

from argparse import ArgumentParser

from fly_in.parsing import MapParser, ParsingError
from fly_in.rendering import render_schedule
from fly_in.rendering.gui.app import render_app
from fly_in.routing import RoutePlanner


def get_args() -> tuple[str, str | None]:
    """Read the map file path from the command-line arguments."""

    parser = ArgumentParser(
        prog="fly-in", description="Drones are interesting"
    )
    parser.add_argument("map", metavar="MAP_FILE", help="map file")
    parser.add_argument(
        "-g",
        "--gui",
        action="store_true",
        help="Display the network and drone positions on graphical interface",
    )
    args = parser.parse_args()

    return str(args.map), args.gui


def main() -> None:
    """Load a map, plan drone routes, and render the resulting schedule."""

    file, gui = get_args()
    map_parser = MapParser(file)

    try:
        map = map_parser.load()
        route_schedule = RoutePlanner(map).plan_routes()

        if route_schedule is None:
            print("No valid route from start to end.")
            return

        render_schedule(route_schedule)

        if gui:
            render_app(map, route_schedule)
    except ParsingError as error:
        print(error)


if __name__ == "__main__":
    main()
