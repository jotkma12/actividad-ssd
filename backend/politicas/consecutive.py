"""Database-backed enforcement for consecutive user-and-space duration."""

from datetime import datetime
import sqlite3

from backend.disponibilidad.intervals import stored_utc
from backend.politicas.validation import validate_consecutive_reservation_limit


def validate_user_space_duration(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_reservation_id: int | None = None,
) -> None:
    """Validate a proposed interval against active reservations in one DB tx."""
    parameters: tuple[int, ...]
    exclusion = ""
    parameters = (user_id, space_id)
    if exclude_reservation_id is not None:
        exclusion = " AND id != ?"
        parameters += (exclude_reservation_id,)
    rows = connection.execute(
        """SELECT starts_at_utc, ends_at_utc FROM reservations
           WHERE user_id = ? AND space_id = ?
             AND status IN ('pending', 'approved')"""
        + exclusion,
        parameters,
    ).fetchall()
    validate_consecutive_reservation_limit(
        starts_at,
        ends_at,
        [
            (stored_utc(row["starts_at_utc"]), stored_utc(row["ends_at_utc"]))
            for row in rows
        ],
    )
