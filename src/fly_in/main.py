"""Provide the Fly-in command-line entry point."""

from argparse import ArgumentParser

from fly_in.parsing import MapParser, ParsingError
from fly_in.rendering import render_html, render_schedule
from fly_in.routing import RoutePlanner


def get_arguments() -> tuple[str, str | None]:
    """Read the map and optional HTML paths from command-line arguments."""

    parser = ArgumentParser(
        prog="fly-in", description="Drones are interesting"
    )
    parser.add_argument("map", help="map file")
    parser.add_argument(
        "--html",
        metavar="FILE",
        help="write an interactive visualization to FILE",
    )
    args = parser.parse_args()

    return str(args.map), args.html


def main() -> None:
    """Load a map, plan drone routes, and render the resulting schedule."""

    file, html_file = get_arguments()
    map_parser = MapParser(file)

    try:
        map = map_parser.load()
        route_schedule = RoutePlanner(map).plan_routes()

        if route_schedule is None:
            print("No valid route from start to end.")
            return

        render_schedule(map, route_schedule)
        if html_file is not None:
            render_html(map, route_schedule, html_file)
    except (OSError, ParsingError) as error:
        print(error)


if __name__ == "__main__":
    main()
