"""Response schemas for read-only audit history."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


HistoryEntityType = Literal["user", "space", "reservation", "maintenance_block"]


class HistoryEventResponse(BaseModel):
    id: int
    actor_user_id: int | None
    actor_full_name: str | None
    actor_role: str | None
    occurred_at_utc: datetime
    entity_type: HistoryEntityType
    entity_id: int
    action: str
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    reason: str | None
