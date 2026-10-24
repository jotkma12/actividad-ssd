"""Reservation approval queue and authorized decisions."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from backend.database import database_connection
from backend.disponibilidad.checks import availability_in_transaction
from backend.disponibilidad.intervals import stored_utc
from backend.historial.records import record_event
from backend.politicas.consecutive import validate_user_space_duration
from backend.politicas.validation import ReservationPolicyError
from backend.reservas.service import get_reservation_record
from backend.reservas.states import (
    EXPIRATION_REASON,
    expire_due_pending_reservations,
)
from backend.usuarios.permissions import Principal


class ApprovalForbiddenError(Exception):
    """The actor is not allowed to inspect or decide this request."""


class ApprovalNotFoundError(Exception):
    """The request does not exist."""


class ApprovalConflictError(Exception):
    """The request is no longer pending."""


class ApprovalReasonRequiredError(Exception):
    """A rejection must include a non-empty reason."""


def list_pending_requests(*, principal: Principal) -> list[dict]:
    if not principal.is_active or principal.role != "approver":
        raise ApprovalForbiddenError
    expire_due_pending_reservations()
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT r.id, r.user_id, r.space_id, s.name AS space_name,
                      r.starts_at_utc, r.ends_at_utc, r.status, r.created_at_utc,
                      r.cancellation_reason
               FROM reservations AS r
               JOIN spaces AS s ON s.id = r.space_id
               JOIN space_approvers AS sa ON sa.space_id = r.space_id
               WHERE r.status = 'pending' AND sa.approver_user_id = ?
               ORDER BY r.starts_at_utc, r.id""",
            (principal.user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_pending_changes(*, principal: Principal) -> list[dict]:
    if not principal.is_active or principal.role != "approver":
        raise ApprovalForbiddenError
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT c.id, r.id AS reservation_id, r.user_id, r.space_id,
                      s.name AS space_name, r.starts_at_utc, r.ends_at_utc,
                      c.starts_at_utc AS proposed_starts_at_utc,
                      c.ends_at_utc AS proposed_ends_at_utc, c.status
               FROM reservation_change_requests AS c
               JOIN reservations AS r ON r.id = c.reservation_id
               JOIN spaces AS s ON s.id = r.space_id
               JOIN space_approvers AS sa ON sa.space_id = r.space_id
               WHERE c.status = 'pending' AND r.status = 'approved'
                 AND sa.approver_user_id = ?
               ORDER BY c.created_at_utc, c.id""",
            (principal.user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def decide_reservation(
    *,
    reservation_id: int,
    principal: Principal,
    decision: str,
    reason: str | None = None,
) -> dict:
    clean_reason = reason.strip() if reason and reason.strip() else None
    if decision == "reject" and clean_reason is None:
        raise ApprovalReasonRequiredError

    expire_due_pending_reservations()
    expired_during_decision = False
    result = None
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        decision_time = datetime.now(timezone.utc)
        actor = connection.execute(
            "SELECT role, is_active FROM users WHERE id = ?", (principal.user_id,)
        ).fetchone()
        if actor is None or actor["role"] != "approver" or not actor["is_active"]:
            raise ApprovalForbiddenError

        reservation = connection.execute(
            """SELECT user_id, space_id, starts_at_utc, status
               FROM reservations WHERE id = ?""",
            (reservation_id,),
        ).fetchone()
        if reservation is None:
            raise ApprovalNotFoundError
        if (
            reservation["status"] == "pending"
            and stored_utc(reservation["starts_at_utc"]) <= decision_time
        ):
            connection.execute(
                """UPDATE reservations SET status = 'rejected_expired'
                   WHERE id = ? AND status = 'pending'""",
                (reservation_id,),
            )
            record_event(
                connection,
                actor_user_id=None,
                entity_type="reservation",
                entity_id=reservation_id,
                action="reservation_expired",
                old_values={"status": "pending"},
                new_values={"status": "rejected_expired"},
                reason=EXPIRATION_REASON,
            )
            expired_during_decision = True
        elif reservation["status"] != "pending":
            raise ApprovalConflictError
        if expired_during_decision:
            pass
        elif reservation["user_id"] == principal.user_id:
            raise ApprovalForbiddenError
        else:
            assigned = connection.execute(
                """SELECT 1 FROM space_approvers
                   WHERE space_id = ? AND approver_user_id = ?""",
                (reservation["space_id"], principal.user_id),
            ).fetchone()
            if assigned is None:
                raise ApprovalForbiddenError

            resulting_status = "approved" if decision == "approve" else "rejected"
            connection.execute(
                "UPDATE reservations SET status = ? WHERE id = ? AND status = 'pending'",
                (resulting_status, reservation_id),
            )
            record_event(
                connection,
                actor_user_id=principal.user_id,
                entity_type="reservation",
                entity_id=reservation_id,
                action=f"reservation_{resulting_status}",
                old_values={"status": "pending"},
                new_values={"status": resulting_status},
                reason=clean_reason if resulting_status == "rejected" else None,
            )
            result = get_reservation_record(connection, reservation_id)
    if expired_during_decision:
        raise ApprovalConflictError
    return result


def decide_reservation_change(
    *,
    change_request_id: int,
    principal: Principal,
    decision: str,
    reason: str | None = None,
) -> dict:
    clean_reason = reason.strip() if reason and reason.strip() else None
    if decision == "reject" and clean_reason is None:
        raise ApprovalReasonRequiredError

    result = None
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        actor = connection.execute(
            "SELECT role, is_active FROM users WHERE id = ?", (principal.user_id,)
        ).fetchone()
        if actor is None or actor["role"] != "approver" or not actor["is_active"]:
            raise ApprovalForbiddenError
        change = connection.execute(
            """SELECT c.id, c.reservation_id, c.starts_at_utc, c.ends_at_utc,
                      c.status, r.user_id, r.space_id, r.starts_at_utc AS original_starts_at,
                      r.ends_at_utc AS original_ends_at, r.status AS reservation_status,
                      s.is_active
               FROM reservation_change_requests AS c
               JOIN reservations AS r ON r.id = c.reservation_id
               JOIN spaces AS s ON s.id = r.space_id
               WHERE c.id = ?""",
            (change_request_id,),
        ).fetchone()
        if change is None:
            raise ApprovalNotFoundError
        if change["status"] != "pending" or change["reservation_status"] != "approved":
            raise ApprovalConflictError
        if change["user_id"] == principal.user_id:
            raise ApprovalForbiddenError
        assigned = connection.execute(
            """SELECT 1 FROM space_approvers
               WHERE space_id = ? AND approver_user_id = ?""",
            (change["space_id"], principal.user_id),
        ).fetchone()
        if assigned is None:
            raise ApprovalForbiddenError

        now_text = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        if decision == "approve":
            if not change["is_active"]:
                raise ApprovalConflictError
            availability = availability_in_transaction(
                connection,
                space_id=change["space_id"],
                starts_at_utc=stored_utc(change["starts_at_utc"]),
                ends_at_utc=stored_utc(change["ends_at_utc"]),
                exclude_reservation_id=change["reservation_id"],
            )
            if availability != "available":
                raise ApprovalConflictError
            try:
                validate_user_space_duration(
                    connection,
                    user_id=change["user_id"],
                    space_id=change["space_id"],
                    starts_at=stored_utc(change["starts_at_utc"]),
                    ends_at=stored_utc(change["ends_at_utc"]),
                    exclude_reservation_id=change["reservation_id"],
                )
            except ReservationPolicyError as error:
                raise ApprovalConflictError from error
            connection.execute(
                """UPDATE reservations SET starts_at_utc = ?, ends_at_utc = ?
                   WHERE id = ? AND status = 'approved'""",
                (
                    change["starts_at_utc"],
                    change["ends_at_utc"],
                    change["reservation_id"],
                ),
            )
            change_status = "approved"
            action = "reservation_change_approved"
            event_reason = None
        else:
            change_status = "rejected"
            action = "reservation_change_rejected"
            event_reason = clean_reason
        connection.execute(
            """UPDATE reservation_change_requests
               SET status = ?, reason = ?, resolved_at_utc = ?
               WHERE id = ? AND status = 'pending'""",
            (change_status, clean_reason, now_text, change_request_id),
        )
        record_event(
            connection,
            actor_user_id=principal.user_id,
            entity_type="reservation",
            entity_id=change["reservation_id"],
            action=action,
            old_values={
                "starts_at_utc": change["original_starts_at"],
                "ends_at_utc": change["original_ends_at"],
                "status": "approved",
            },
            new_values={
                "starts_at_utc": change["starts_at_utc"] if decision == "approve" else change["original_starts_at"],
                "ends_at_utc": change["ends_at_utc"] if decision == "approve" else change["original_ends_at"],
                "change_status": change_status,
            },
            reason=event_reason,
        )
        result = get_reservation_record(connection, change["reservation_id"])
    return result
