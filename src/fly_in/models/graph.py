from pydantic import BaseModel, Field
from .zone import Zone
from .connection import Connection


class Graph(BaseModel):
    nb_drones: int = Field(ge=1)
    zones: dict[str, Zone]
    connections: list[Connection]
    start: Zone
    end: Zone
