from argparse import ArgumentParser

from fly_in.parsing.map_parser import MapParser, ParsingError


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
        print(map.model_dump_json(indent=2))
    except ParsingError as error:
        print(error)


if __name__ == "__main__":
    main()
