"""Availability calculation that can run inside a caller's SQLite transaction."""

from datetime import datetime
import sqlite3

from backend.disponibilidad.intervals import intervals_overlap, stored_utc


def availability_in_transaction(
    connection: sqlite3.Connection,
    *,
    space_id: int,
    starts_at_utc: datetime,
    ends_at_utc: datetime,
    exclude_reservation_id: int | None = None,
) -> str:
    """Return available, occupied, or blocked using the caller's transaction."""
    if exclude_reservation_id is None:
        reservations = connection.execute(
            """SELECT starts_at_utc, ends_at_utc FROM reservations
               WHERE space_id = ? AND status IN ('pending', 'approved')""",
            (space_id,),
        ).fetchall()
    else:
        reservations = connection.execute(
            """SELECT starts_at_utc, ends_at_utc FROM reservations
               WHERE space_id = ? AND id != ?
                 AND status IN ('pending', 'approved')""",
            (space_id, exclude_reservation_id),
        ).fetchall()
    has_reservation = any(
        intervals_overlap(
            starts_at_utc,
            ends_at_utc,
            stored_utc(row["starts_at_utc"]),
            stored_utc(row["ends_at_utc"]),
        )
        for row in reservations
    )

    if exclude_reservation_id is None:
        pending_changes = connection.execute(
            """SELECT c.starts_at_utc, c.ends_at_utc
               FROM reservation_change_requests AS c
               JOIN reservations AS r ON r.id = c.reservation_id
               WHERE r.space_id = ? AND r.status = 'approved'
                 AND c.status = 'pending'""",
            (space_id,),
        ).fetchall()
    else:
        pending_changes = connection.execute(
            """SELECT c.starts_at_utc, c.ends_at_utc
               FROM reservation_change_requests AS c
               JOIN reservations AS r ON r.id = c.reservation_id
               WHERE r.space_id = ? AND r.status = 'approved'
                 AND r.id != ? AND c.status = 'pending'""",
            (space_id, exclude_reservation_id),
        ).fetchall()
    has_pending_change = any(
        intervals_overlap(
            starts_at_utc,
            ends_at_utc,
            stored_utc(row["starts_at_utc"]),
            stored_utc(row["ends_at_utc"]),
        )
        for row in pending_changes
    )

    blocks = connection.execute(
        """SELECT starts_at_utc, ends_at_utc FROM maintenance_blocks
           WHERE space_id = ?""",
        (space_id,),
    ).fetchall()
    has_maintenance = any(
        intervals_overlap(
            starts_at_utc,
            ends_at_utc,
            stored_utc(row["starts_at_utc"]),
            stored_utc(row["ends_at_utc"]),
        )
        for row in blocks
    )
    return (
        "blocked"
        if has_maintenance
        else "occupied"
        if has_reservation or has_pending_change
        else "available"
    )
