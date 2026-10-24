"""Reservation state transitions driven by the passage of time."""

from datetime import datetime, timezone
import sqlite3

from backend.disponibilidad.intervals import to_utc
from backend.database import database_connection
from backend.historial.records import record_event


EXPIRATION_REASON = "Solicitud rechazada por vencimiento al llegar su hora de inicio."


def finalize_expired_approved(
    connection: sqlite3.Connection, *, now: datetime
) -> None:
    """Finalize approved reservations whose end instant has elapsed."""
    instant = to_utc(now).isoformat(timespec="microseconds")
    expired = connection.execute(
        """SELECT id FROM reservations
           WHERE status = 'approved' AND ends_at_utc <= ?""",
        (instant,),
    ).fetchall()
    for reservation in expired:
        cancel_pending_reservation_changes(
            connection,
            reservation_id=reservation["id"],
            actor_user_id=None,
            reason="La reserva original finalizó antes de resolver el cambio.",
            now=now,
        )
    connection.execute(
        """UPDATE reservations SET status = 'finished'
           WHERE status = 'approved' AND ends_at_utc <= ?""",
        (instant,),
    )


def cancel_pending_reservation_changes(
    connection: sqlite3.Connection,
    *,
    reservation_id: int,
    actor_user_id: int | None,
    reason: str,
    now: datetime | None = None,
) -> int:
    """Release pending proposed intervals when their original reservation closes."""
    resolved_at = to_utc(now or datetime.now(timezone.utc)).isoformat(
        timespec="microseconds"
    )
    changes = connection.execute(
        """SELECT id FROM reservation_change_requests
           WHERE reservation_id = ? AND status = 'pending'""",
        (reservation_id,),
    ).fetchall()
    for change in changes:
        connection.execute(
            """UPDATE reservation_change_requests
               SET status = 'cancelled', reason = ?, resolved_at_utc = ?
               WHERE id = ? AND status = 'pending'""",
            (reason, resolved_at, change["id"]),
        )
        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="reservation",
            entity_id=reservation_id,
            action="reservation_change_cancelled",
            old_values={"change_request_id": change["id"], "status": "pending"},
            new_values={"change_request_id": change["id"], "status": "cancelled"},
            reason=reason,
        )
    return len(changes)


def expire_due_pending_in_transaction(
    connection: sqlite3.Connection, *, now: datetime
) -> int:
    """Reject due requests in the caller's write transaction and audit each one."""
    instant = to_utc(now)
    candidates = connection.execute(
        "SELECT id, starts_at_utc, ends_at_utc FROM reservations WHERE status = 'pending'"
    ).fetchall()
    expired = 0
    for row in candidates:
        if to_utc(datetime.fromisoformat(row["starts_at_utc"])) > instant:
            continue
        cursor = connection.execute(
            """UPDATE reservations SET status = 'rejected_expired'
               WHERE id = ? AND status = 'pending'""",
            (row["id"],),
        )
        if cursor.rowcount != 1:
            continue
        record_event(
            connection,
            actor_user_id=None,
            entity_type="reservation",
            entity_id=row["id"],
            action="reservation_expired",
            old_values={"status": "pending"},
            new_values={"status": "rejected_expired"},
            reason=EXPIRATION_REASON,
        )
        expired += 1
    return expired


def expire_due_pending_reservations(*, now: datetime | None = None) -> int:
    """Apply due pending-request expirations in an atomic SQLite transaction."""
    instant = to_utc(now or datetime.now(timezone.utc))
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        return expire_due_pending_in_transaction(connection, now=instant)
