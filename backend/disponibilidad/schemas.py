"""Availability response models."""

from typing import Literal

from pydantic import BaseModel


class AvailabilityResponse(BaseModel):
    space_id: int
    starts_at_utc: str
    ends_at_utc: str
    availability: Literal["available", "occupied", "blocked"]
    is_available: bool
