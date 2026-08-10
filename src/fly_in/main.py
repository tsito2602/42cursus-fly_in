from pydantic import ValidationError
from fly_in.parsing.map_parser import (
    MapParser,
    get_map_file,
    ParsingError,
)


def main() -> None:
    file = get_map_file()
    map_parser = MapParser(file)

    try:
        map = map_parser.load()
        print(map.model_dump_json(indent=2))
    except (ParsingError, ValidationError) as error:
        print(error)


if __name__ == "__main__":
    main()
