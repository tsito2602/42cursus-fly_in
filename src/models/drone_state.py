from pydantic import BaseModel, Field

from .connection import Connection
from .zone import Zone


class DroneStete(BaseModel):
    drone_id: int = Field(ge=1)
    location: Zone | Connection
    destination: Zone | Connection
