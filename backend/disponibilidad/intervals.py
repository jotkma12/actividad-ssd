"""Shared timezone normalization and half-open interval comparison."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("America/Bogota")


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=LOCAL_TIMEZONE)
    return value.astimezone(timezone.utc)


def stored_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def intervals_overlap(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    """Use the plan's half-open rule: A.start < B.end and B.start < A.end."""
    return first_start < second_end and second_start < first_end
