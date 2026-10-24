"""Reservation request and response models."""

from typing import Literal

from pydantic import BaseModel, field_validator


ReservationStatus = Literal["pending", "approved", "rejected", "cancelled", "finished"]


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    space_id: int
    space_name: str
    starts_at_utc: str
    ends_at_utc: str
    status: ReservationStatus
    created_at_utc: str
    cancellation_reason: str | None


class CancellationRequest(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
