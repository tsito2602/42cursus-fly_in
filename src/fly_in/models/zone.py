from enum import Enum
from pydantic import BaseModel, Field


class ZoneRole(Enum):
    START = "start"
    END = "end"
    HUB = "hub"


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone(BaseModel):
    name: str = Field(min_length=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    zone_role: ZoneRole
    zone_type: ZoneType
    color: str
    capacity: int | None = Field(ge=1)
