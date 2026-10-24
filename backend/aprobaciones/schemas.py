"""Request models for reservation decisions."""

from typing import Literal

from pydantic import BaseModel, field_validator


class ReservationDecision(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PendingReservationChangeResponse(BaseModel):
    id: int
    reservation_id: int
    user_id: int
    space_id: int
    space_name: str
    starts_at_utc: str
    ends_at_utc: str
    proposed_starts_at_utc: str
    proposed_ends_at_utc: str
    status: Literal["pending"]
