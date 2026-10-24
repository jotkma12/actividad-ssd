"""Reservation persistence, visibility, finalization, and cancellation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from backend.database import database_connection
from backend.disponibilidad.checks import availability_in_transaction
from backend.historial.records import record_event
from backend.politicas.approval import initial_reservation_status
from backend.politicas.validation import validate_reservation_interval
from backend.reservas.states import (
    cancel_pending_reservation_changes,
    expire_due_pending_reservations,
    finalize_expired_approved,
)
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


class ReservationSpaceNotFoundError(Exception):
    """The requested space does not exist."""


class ReservationSpaceInactiveError(Exception):
    """The requested space is inactive."""


class ReservationCreationForbiddenError(Exception):
    """Only active requester accounts may submit reservation requests."""


class ReservationContentionError(Exception):
    """SQLite could not acquire its write lock before the configured timeout."""


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
    result = dict(row)
    change_id = result.pop("pending_change_id", None)
    change_starts = result.pop("pending_change_starts_at_utc", None)
    change_ends = result.pop("pending_change_ends_at_utc", None)
    if change_id is not None:
        result["pending_change"] = {
            "id": change_id,
            "starts_at_utc": change_starts,
            "ends_at_utc": change_ends,
            "status": "pending",
        }
    else:
        result["pending_change"] = None
    return result


def create_reservation(
    *,
    user_id: int,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
    created_at: datetime | None = None,
) -> dict:
    """Atomically validate and persist a reservation request."""
    requested_at = _as_utc(created_at or datetime.now(timezone.utc))
    starts_at_utc, ends_at_utc = validate_reservation_interval(
        starts_at, ends_at, requested_at=requested_at
    )
    created_at_text = _utc_text(requested_at)
    try:
        expire_due_pending_reservations(now=requested_at)
        with database_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT role, is_active FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if user is None or user["role"] != "requester" or not user["is_active"]:
                raise ReservationCreationForbiddenError
            space = connection.execute(
                "SELECT is_active, requires_approval FROM spaces WHERE id = ?",
                (space_id,),
            ).fetchone()
            if space is None:
                raise ReservationSpaceNotFoundError
            if not space["is_active"]:
                raise ReservationSpaceInactiveError

            finalize_expired_approved(connection, now=requested_at)
            availability = availability_in_transaction(
                connection,
                space_id=space_id,
                starts_at_utc=starts_at_utc,
                ends_at_utc=ends_at_utc,
            )
            if availability != "available":
                raise ReservationConflictError(
                    "El intervalo está ocupado por una reserva o bloqueado por mantenimiento"
                )

            initial_status = initial_reservation_status(
                bool(space["requires_approval"])
            )
            cursor = connection.execute(
                """INSERT INTO reservations (
                       user_id, space_id, starts_at_utc, ends_at_utc, status,
                       created_at_utc
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    space_id,
                    _utc_text(starts_at_utc),
                    _utc_text(ends_at_utc),
                    initial_status,
                    created_at_text,
                ),
            )
            reservation_id = cursor.lastrowid
            record_event(
                connection,
                actor_user_id=user_id,
                entity_type="reservation",
                entity_id=reservation_id,
                action="reservation_created",
                old_values=None,
                new_values={
                    "space_id": space_id,
                    "starts_at_utc": _utc_text(starts_at_utc),
                    "ends_at_utc": _utc_text(ends_at_utc),
                    "status": initial_status,
                },
            )
            return get_reservation_record(connection, reservation_id)
    except sqlite3.OperationalError as error:
        if "locked" in str(error).lower() or "busy" in str(error).lower():
            raise ReservationContentionError from error
        raise


def get_reservation_record(connection: sqlite3.Connection, reservation_id: int) -> dict:
    row = connection.execute(
        """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                  r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                  r.cancellation_reason,
                  c.id AS pending_change_id,
                  c.starts_at_utc AS pending_change_starts_at_utc,
                  c.ends_at_utc AS pending_change_ends_at_utc
           FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
           LEFT JOIN reservation_change_requests AS c
             ON c.reservation_id = r.id AND c.status = 'pending'
            AND r.status = 'approved'
           WHERE r.id = ?""",
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ReservationNotFoundError("La reserva no existe")
    return _reservation_dict(row)


def list_reservations(*, principal: Principal, now: datetime | None = None) -> list[dict]:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    expire_due_pending_reservations(now=current_time)
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        finalize_expired_approved(connection, now=current_time)
        if not principal.is_active:
            return []
        if principal.role == "administrator":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason,
                          c.id AS pending_change_id,
                          c.starts_at_utc AS pending_change_starts_at_utc,
                          c.ends_at_utc AS pending_change_ends_at_utc
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   LEFT JOIN reservation_change_requests AS c
                     ON c.reservation_id = r.id AND c.status = 'pending'
                    AND r.status = 'approved'
                   ORDER BY r.starts_at_utc, r.id"""
            ).fetchall()
        elif principal.role == "requester":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason,
                          c.id AS pending_change_id,
                          c.starts_at_utc AS pending_change_starts_at_utc,
                          c.ends_at_utc AS pending_change_ends_at_utc
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   LEFT JOIN reservation_change_requests AS c
                     ON c.reservation_id = r.id AND c.status = 'pending'
                    AND r.status = 'approved'
                   WHERE r.user_id = ? ORDER BY r.starts_at_utc, r.id""",
                (principal.user_id,),
            ).fetchall()
        elif principal.role == "approver":
            rows = connection.execute(
                """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                          r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                          r.cancellation_reason,
                          c.id AS pending_change_id,
                          c.starts_at_utc AS pending_change_starts_at_utc,
                          c.ends_at_utc AS pending_change_ends_at_utc
                   FROM reservations AS r JOIN spaces AS s ON s.id = r.space_id
                   JOIN space_approvers AS sa ON sa.space_id = r.space_id
                   LEFT JOIN reservation_change_requests AS c
                     ON c.reservation_id = r.id AND c.status = 'pending'
                    AND r.status = 'approved'
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


def update_reservation(
    *,
    reservation_id: int,
    actor_user_id: int,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> dict:
    """Change a requester's pending or eligible approved reservation."""
    current_time = _as_utc(now or datetime.now(timezone.utc))
    starts_at_utc, ends_at_utc = validate_reservation_interval(
        starts_at, ends_at, requested_at=current_time
    )
    expire_due_pending_reservations(now=current_time)
    updated = None
    finalized = False
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        reservation = connection.execute(
            """SELECT id, user_id, space_id, starts_at_utc, ends_at_utc, status
               FROM reservations WHERE id = ?""",
            (reservation_id,),
        ).fetchone()
        if reservation is None or reservation["user_id"] != actor_user_id:
            raise ReservationNotFoundError("La reserva no existe")
        status = reservation["status"]
        if (
            status == "approved"
            and _parse_utc(reservation["ends_at_utc"]) <= current_time
        ):
            connection.execute(
                "UPDATE reservations SET status = 'finished' WHERE id = ?",
                (reservation_id,),
            )
            updated = get_reservation_record(connection, reservation_id)
            finalized = True
        elif status not in {"pending", "approved"}:
            raise ReservationConflictError("La reserva ya no se puede modificar")
        else:
            space = connection.execute(
                "SELECT is_active, requires_approval FROM spaces WHERE id = ?",
                (reservation["space_id"],),
            ).fetchone()
            if space is None:
                raise ReservationSpaceNotFoundError
            if not space["is_active"]:
                raise ReservationSpaceInactiveError
            if status == "approved":
                if (
                    _parse_utc(reservation["starts_at_utc"]) - current_time
                    < CANCELLATION_CUTOFF
                ):
                    raise ReservationConflictError(
                        "La reserva aprobada solo se puede modificar hasta dos horas antes"
                    )
            availability = availability_in_transaction(
                connection,
                space_id=reservation["space_id"],
                starts_at_utc=starts_at_utc,
                ends_at_utc=ends_at_utc,
                exclude_reservation_id=reservation_id,
            )
            if availability != "available":
                raise ReservationConflictError(
                    "El nuevo intervalo está ocupado o bloqueado por mantenimiento"
                )
            if status == "approved" and space["requires_approval"]:
                existing_change = connection.execute(
                    """SELECT id FROM reservation_change_requests
                       WHERE reservation_id = ? AND status = 'pending'""",
                    (reservation_id,),
                ).fetchone()
                if existing_change is not None:
                    raise ReservationConflictError(
                        "La reserva ya tiene un cambio pendiente de aprobación"
                    )
                proposed_starts = _utc_text(starts_at_utc)
                proposed_ends = _utc_text(ends_at_utc)
                cursor = connection.execute(
                    """INSERT INTO reservation_change_requests (
                           reservation_id, starts_at_utc, ends_at_utc, status,
                           created_at_utc
                       ) VALUES (?, ?, ?, 'pending', ?)""",
                    (
                        reservation_id,
                        proposed_starts,
                        proposed_ends,
                        _utc_text(current_time),
                    ),
                )
                record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    entity_type="reservation",
                    entity_id=reservation_id,
                    action="reservation_change_requested",
                    old_values={
                        "starts_at_utc": reservation["starts_at_utc"],
                        "ends_at_utc": reservation["ends_at_utc"],
                        "status": "approved",
                    },
                    new_values={
                        "change_request_id": cursor.lastrowid,
                        "starts_at_utc": proposed_starts,
                        "ends_at_utc": proposed_ends,
                        "status": "pending",
                    },
                )
                updated = get_reservation_record(connection, reservation_id)
            else:
                old_values = {
                    "starts_at_utc": reservation["starts_at_utc"],
                    "ends_at_utc": reservation["ends_at_utc"],
                    "status": status,
                }
                connection.execute(
                    """UPDATE reservations SET starts_at_utc = ?, ends_at_utc = ?
                       WHERE id = ?""",
                    (_utc_text(starts_at_utc), _utc_text(ends_at_utc), reservation_id),
                )
                record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    entity_type="reservation",
                    entity_id=reservation_id,
                    action="reservation_updated",
                    old_values=old_values,
                    new_values={
                        "starts_at_utc": _utc_text(starts_at_utc),
                        "ends_at_utc": _utc_text(ends_at_utc),
                        "status": status,
                    },
                )
                updated = get_reservation_record(connection, reservation_id)

    if finalized:
        raise ReservationConflictError("La reserva ya terminó y fue finalizada")
    return updated


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
            cancel_pending_reservation_changes(
                connection,
                reservation_id=reservation_id,
                actor_user_id=actor_user_id,
                reason=clean_reason or "La reserva original fue cancelada.",
                now=current_time,
            )
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
