"""Define the state of one drone."""

from pydantic import BaseModel, Field

from .connection import Connection
from .zone import Zone


class DroneState(BaseModel):
    """Represent a drone's current location and destination."""

    drone_id: int = Field(ge=1)
    location: Zone | Connection
    destination: Zone | Connection
