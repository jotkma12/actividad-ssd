"""Availability checks for reservations and maintenance intervals."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import database_connection
from backend.disponibilidad.intervals import intervals_overlap, stored_utc, to_utc
from backend.reservas.service import finalize_expired_approved


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

        reservations = connection.execute(
            """SELECT starts_at_utc, ends_at_utc FROM reservations
               WHERE space_id = ? AND status IN ('pending', 'approved')""",
            (space_id,),
        ).fetchall()
        has_reservation = any(
            intervals_overlap(
                proposed_start,
                proposed_end,
                stored_utc(row["starts_at_utc"]),
                stored_utc(row["ends_at_utc"]),
            )
            for row in reservations
        )

        blocks = connection.execute(
            """SELECT starts_at_utc, ends_at_utc FROM maintenance_blocks
               WHERE space_id = ?""",
            (space_id,),
        ).fetchall()
        has_maintenance = any(
            intervals_overlap(
                proposed_start,
                proposed_end,
                stored_utc(row["starts_at_utc"]),
                stored_utc(row["ends_at_utc"]),
            )
            for row in blocks
        )

    availability = (
        "blocked" if has_maintenance else "occupied" if has_reservation else "available"
    )
    return {
        "space_id": space_id,
        "starts_at_utc": proposed_start.isoformat(timespec="microseconds"),
        "ends_at_utc": proposed_end.isoformat(timespec="microseconds"),
        "availability": availability,
        "is_available": availability == "available",
    }
