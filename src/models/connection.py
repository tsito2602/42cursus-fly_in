from pydantic import BaseModel, Field
from .zone import Zone


class Connection(BaseModel):
    zone_a: Zone
    zone_b: Zone
    capacity: int = Field(default=1, ge=1)
