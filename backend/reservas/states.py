"""Reservation state transitions driven by the passage of time."""

from datetime import datetime, timezone
import sqlite3

from backend.disponibilidad.intervals import to_utc


def finalize_expired_approved(
    connection: sqlite3.Connection, *, now: datetime
) -> None:
    """Finalize approved reservations whose end instant has elapsed."""
    connection.execute(
        """UPDATE reservations SET status = 'finished'
           WHERE status = 'approved' AND ends_at_utc <= ?""",
        (to_utc(now).isoformat(timespec="microseconds"),),
    )
