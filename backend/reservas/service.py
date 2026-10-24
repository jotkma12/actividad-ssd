"""Reservation persistence, visibility, finalization, and cancellation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from backend.database import database_connection
from backend.historial.records import record_event
from backend.politicas.approval import initial_reservation_status
from backend.politicas.validation import validate_reservation_interval
from backend.usuarios.permissions import Principal


CANCELLATION_CUTOFF = timedelta(hours=2)
class ReservationNotFoundError(Exception):
    """The reservation does not exist or is outside the caller's visibility."""


class ReservationConflictError(Exception):
    """The requested cancellation is not valid for the reservation state/time."""


class ReservationForbiddenError(Exception):
    """The caller cannot cancel this reservation."""


class CancellationReasonRequiredError(Exception):
    """Administrative cancellation requires a non-empty reason."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La hora actual debe incluir una zona horaria")
    return value.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="microseconds")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _reservation_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def create_reservation(
    *,
    user_id: int,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
    created_at: datetime | None = None,
) -> dict:
    """Persist a reservation record using the space's current approval rule.

    Availability and request authorization are validated by the later booking
    workflow. This domain operation centralizes policy validation and storage.
    """
    requested_at = _as_utc(created_at or datetime.now(timezone.utc))
    starts_at_utc, ends_at_utc = validate_reservation_interval(
        starts_at, ends_at, requested_at=requested_at
    )
    created_at_text = _utc_text(requested_at)
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        space = connection.execute(
            "SELECT requires_approval FROM spaces WHERE id = ?", (space_id,)
        ).fetchone()
        if space is None:
            raise ReservationNotFoundError("El espacio no existe")
        status = initial_reservation_status(bool(space["requires_approval"]))
        cursor = connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                space_id,
                _utc_text(starts_at_utc),
                _utc_text(ends_at_utc),
                status,
                created_at_text,
            ),
        )
        return get_reservation_record(connection, cursor.lastrowid)


def get_reservation_record(connection: sqlite3.Connection, reservation_id: int) -> dict:
    row = connection.execute(
        """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                  r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                  r.cancellation_reason
           FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
           WHERE r.id = ?""",
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ReservationNotFoundError("La reserva no existe")
    return _reservation_dict(row)


def _finalize_expired_approved(
    connection: sqlite3.Connection, *, now: datetime
) -> None:
    connection.execute(
        """UPDATE reservations SET status = 'finished'
           WHERE status = 'approved' AND ends_at_utc <= ?""",
        (_utc_text(now),),
    )


def list_reservations(*, principal: Principal, now: datetime | None = None) -> list[dict]:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _finalize_expired_approved(connection, now=current_time)
        if not principal.is_active:
            return []
        if principal.role == "administrator":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   ORDER BY r.starts_at_utc, r.id"""
            ).fetchall()
        elif principal.role == "requester":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   WHERE r.user_id = ? ORDER BY r.starts_at_utc, r.id""",
                (principal.user_id,),
            ).fetchall()
        elif principal.role == "approver":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   JOIN space_approvers AS sa ON sa.space_id = r.space_id
                   WHERE sa.approver_user_id = ?
                   ORDER BY r.starts_at_utc, r.id""",
                (principal.user_id,),
            ).fetchall()
        else:
            return []
        return [_reservation_dict(row) for row in rows]


def get_reservation(
    *, principal: Principal, reservation_id: int, now: datetime | None = None
) -> dict:
    visible_ids = {item["id"] for item in list_reservations(principal=principal, now=now)}
    if reservation_id not in visible_ids:
        raise ReservationNotFoundError("La reserva no existe")
    with database_connection() as connection:
        return get_reservation_record(connection, reservation_id)


def cancel_reservation(
    *,
    reservation_id: int,
    actor_user_id: int,
    actor_role: str,
    reason: str | None = None,
    now: datetime | None = None,
) -> dict:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    clean_reason = reason.strip() if reason and reason.strip() else None
    if actor_role == "administrator" and clean_reason is None:
        raise CancellationReasonRequiredError
    if actor_role not in {"administrator", "requester"}:
        raise ReservationForbiddenError

    conflict_after_finalize = False
    cancelled_result = None
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        reservation = connection.execute(
            """SELECT id, user_id, space_id, starts_at_utc, ends_at_utc, status,
                      cancellation_reason
               FROM reservations WHERE id = ?""",
            (reservation_id,),
        ).fetchone()
        if reservation is None:
            raise ReservationNotFoundError("La reserva no existe")
        if actor_role == "requester" and reservation["user_id"] != actor_user_id:
            raise ReservationNotFoundError("La reserva no existe")

        current = reservation["status"]
        if (
            current == "approved"
            and _parse_utc(reservation["ends_at_utc"]) <= current_time
        ):
            connection.execute(
                "UPDATE reservations SET status = 'finished' WHERE id = ?",
                (reservation_id,),
            )
            cancelled_result = get_reservation_record(connection, reservation_id)
            conflict_after_finalize = True
        elif current not in {"pending", "approved"}:
            raise ReservationConflictError("La reserva ya no se puede cancelar")
        elif (
            actor_role == "requester"
            and current == "approved"
            and _parse_utc(reservation["starts_at_utc"]) - current_time
            < CANCELLATION_CUTOFF
        ):
            raise ReservationConflictError(
                "La reserva aprobada solo se puede cancelar hasta dos horas antes"
            )
        else:
            connection.execute(
                """UPDATE reservations SET status = 'cancelled', cancellation_reason = ?
                   WHERE id = ?""",
                (clean_reason, reservation_id),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="reservation",
                entity_id=reservation_id,
                action="reservation_cancelled",
                old_values={"status": current},
                new_values={"status": "cancelled", "cancellation_reason": clean_reason},
            )
            cancelled_result = get_reservation_record(connection, reservation_id)

    if conflict_after_finalize:
        raise ReservationConflictError(
            "La reserva ya terminó y fue finalizada"
        )
    return cancelled_result
