"""Availability checks for reservations and maintenance intervals."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import database_connection
from backend.disponibilidad.checks import availability_in_transaction
from backend.disponibilidad.intervals import to_utc
from backend.reservas.states import finalize_expired_approved


class AvailabilitySpaceNotFoundError(Exception):
    """The requested space does not exist."""


class InactiveAvailabilitySpaceError(Exception):
    """The requested space is inactive and cannot be booked."""


def query_availability(
    *,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> dict:
    """Report whether an active space interval is free, occupied, or blocked."""
    proposed_start = to_utc(starts_at)
    proposed_end = to_utc(ends_at)
    if proposed_start >= proposed_end:
        raise ValueError("El inicio debe ser anterior al fin del intervalo")
    current_time = to_utc(now or datetime.now(timezone.utc))

    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        space = connection.execute(
            "SELECT is_active FROM spaces WHERE id = ?", (space_id,)
        ).fetchone()
        if space is None:
            raise AvailabilitySpaceNotFoundError
        if not space["is_active"]:
            raise InactiveAvailabilitySpaceError
        finalize_expired_approved(connection, now=current_time)

        availability = availability_in_transaction(
            connection,
            space_id=space_id,
            starts_at_utc=proposed_start,
            ends_at_utc=proposed_end,
        )

    return {
        "space_id": space_id,
        "starts_at_utc": proposed_start.isoformat(timespec="microseconds"),
        "ends_at_utc": proposed_end.isoformat(timespec="microseconds"),
        "availability": availability,
        "is_available": availability == "available",
    }
