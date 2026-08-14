"""Define connections between zones."""

from pydantic import BaseModel, Field, model_validator


class Connection(BaseModel):
    """Represent a bidirectional connection with a traversal capacity."""

    zone_a: str
    zone_b: str
    capacity: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_zones(self) -> "Connection":
        """Reject a connection whose endpoints are the same zone."""

        if self.zone_a == self.zone_b:
            raise ValueError("Connection endpoints must be different.")

        return self
