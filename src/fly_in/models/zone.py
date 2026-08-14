"""Define zone roles, movement types, and attributes."""

from enum import Enum
from pydantic import BaseModel, Field


class ZoneRole(Enum):
    """Identify whether a zone is the start, end, or an intermediate hub."""

    START = "start"
    END = "end"
    HUB = "hub"


class ZoneType(Enum):
    """Describe the movement behavior associated with a zone."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone(BaseModel):
    """Represent a named location and its simulation constraints."""

    name: str = Field(min_length=1)
    x: int
    y: int
    zone_role: ZoneRole
    zone_type: ZoneType = Field(default=ZoneType.NORMAL)
    color: str | None
    capacity: int | None = Field(default=1, ge=1)
