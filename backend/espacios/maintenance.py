"""Maintenance-block persistence and conflict checks."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from backend.database import database_connection
from backend.disponibilidad.intervals import intervals_overlap, stored_utc, to_utc
from backend.historial.records import record_event
from backend.espacios.service import SpaceNotFoundError


class MaintenanceBlockNotFoundError(Exception):
    """The requested maintenance block does not exist for the given space."""


class MaintenanceConflictError(Exception):
    """Pending or approved reservations overlap the requested block interval."""

    def __init__(self, reservations: list[dict]):
        super().__init__("El intervalo se cruza con reservas pendientes o aprobadas")
        self.reservations = reservations


def _utc_datetime(value: datetime) -> datetime:
    return to_utc(value)


def _stored_datetime(value: str) -> datetime:
    return stored_utc(value)


def _block_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _conflicts(
    connection: sqlite3.Connection,
    *,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
) -> list[dict]:
    candidates = connection.execute(
        """SELECT id, status, starts_at_utc, ends_at_utc FROM reservations
           WHERE space_id = ? AND status IN ('pending', 'approved')""",
        (space_id,),
    ).fetchall()
    overlaps = []
    for reservation in candidates:
        reservation_start = _stored_datetime(reservation["starts_at_utc"])
        reservation_end = _stored_datetime(reservation["ends_at_utc"])
        if intervals_overlap(
            starts_at, ends_at, reservation_start, reservation_end
        ):
            overlaps.append(
                {"id": reservation["id"], "status": reservation["status"]}
            )
    return overlaps


def _ensure_space_exists(connection: sqlite3.Connection, space_id: int) -> None:
    if connection.execute("SELECT 1 FROM spaces WHERE id = ?", (space_id,)).fetchone() is None:
        raise SpaceNotFoundError


def list_maintenance_blocks(space_id: int) -> list[dict]:
    with database_connection() as connection:
        _ensure_space_exists(connection, space_id)
        rows = connection.execute(
            """SELECT id, space_id, starts_at_utc, ends_at_utc, reason, created_at_utc
               FROM maintenance_blocks WHERE space_id = ?
               ORDER BY starts_at_utc, id""",
            (space_id,),
        ).fetchall()
        return [_block_dict(row) for row in rows]


def create_maintenance_block(
    *,
    actor_user_id: int,
    space_id: int,
    starts_at: datetime,
    ends_at: datetime,
    reason: str,
) -> dict:
    starts_at_utc = _utc_datetime(starts_at)
    ends_at_utc = _utc_datetime(ends_at)
    if starts_at_utc >= ends_at_utc:
        raise ValueError("El inicio debe ser anterior al fin del bloqueo")

    starts_text = starts_at_utc.isoformat(timespec="microseconds")
    ends_text = ends_at_utc.isoformat(timespec="microseconds")
    created_at = datetime.now(timezone.utc).isoformat()
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_space_exists(connection, space_id)
        conflicts = _conflicts(
            connection,
            space_id=space_id,
            starts_at=starts_at_utc,
            ends_at=ends_at_utc,
        )
        if conflicts:
            raise MaintenanceConflictError(conflicts)

        cursor = connection.execute(
            """INSERT INTO maintenance_blocks (
                   space_id, starts_at_utc, ends_at_utc, reason, created_at_utc
               ) VALUES (?, ?, ?, ?, ?)""",
            (space_id, starts_text, ends_text, reason.strip(), created_at),
        )
        block_id = cursor.lastrowid
        new_values = {
            "starts_at_utc": starts_text,
            "ends_at_utc": ends_text,
            "reason": reason.strip(),
        }
        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="maintenance_block",
            entity_id=block_id,
            action="maintenance_block_created",
            old_values=None,
            new_values=new_values,
        )
        row = connection.execute(
            """SELECT id, space_id, starts_at_utc, ends_at_utc, reason, created_at_utc
               FROM maintenance_blocks WHERE id = ?""",
            (block_id,),
        ).fetchone()
        return _block_dict(row)


def update_maintenance_block(
    *,
    actor_user_id: int,
    space_id: int,
    block_id: int,
    starts_at: datetime,
    ends_at: datetime,
    reason: str,
) -> dict:
    starts_at_utc = _utc_datetime(starts_at)
    ends_at_utc = _utc_datetime(ends_at)
    if starts_at_utc >= ends_at_utc:
        raise ValueError("El inicio debe ser anterior al fin del bloqueo")

    starts_text = starts_at_utc.isoformat(timespec="microseconds")
    ends_text = ends_at_utc.isoformat(timespec="microseconds")
    normalized_reason = reason.strip()
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_space_exists(connection, space_id)
        existing = connection.execute(
            """SELECT id, space_id, starts_at_utc, ends_at_utc, reason, created_at_utc
               FROM maintenance_blocks WHERE id = ? AND space_id = ?""",
            (block_id, space_id),
        ).fetchone()
        if existing is None:
            raise MaintenanceBlockNotFoundError

        conflicts = _conflicts(
            connection,
            space_id=space_id,
            starts_at=starts_at_utc,
            ends_at=ends_at_utc,
        )
        if conflicts:
            raise MaintenanceConflictError(conflicts)

        old_values = {
            "starts_at_utc": existing["starts_at_utc"],
            "ends_at_utc": existing["ends_at_utc"],
            "reason": existing["reason"],
        }
        new_values = {
            "starts_at_utc": starts_text,
            "ends_at_utc": ends_text,
            "reason": normalized_reason,
        }
        if old_values != new_values:
            connection.execute(
                """UPDATE maintenance_blocks
                   SET starts_at_utc = ?, ends_at_utc = ?, reason = ?
                   WHERE id = ? AND space_id = ?""",
                (starts_text, ends_text, normalized_reason, block_id, space_id),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="maintenance_block",
                entity_id=block_id,
                action="maintenance_block_updated",
                old_values=old_values,
                new_values=new_values,
            )

        row = connection.execute(
            """SELECT id, space_id, starts_at_utc, ends_at_utc, reason, created_at_utc
               FROM maintenance_blocks WHERE id = ?""",
            (block_id,),
        ).fetchone()
        return _block_dict(row)


def delete_maintenance_block(
    *, actor_user_id: int, space_id: int, block_id: int
) -> None:
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_space_exists(connection, space_id)
        existing = connection.execute(
            """SELECT id, starts_at_utc, ends_at_utc, reason
               FROM maintenance_blocks WHERE id = ? AND space_id = ?""",
            (block_id, space_id),
        ).fetchone()
        if existing is None:
            raise MaintenanceBlockNotFoundError

        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="maintenance_block",
            entity_id=block_id,
            action="maintenance_block_deleted",
            old_values={
                "starts_at_utc": existing["starts_at_utc"],
                "ends_at_utc": existing["ends_at_utc"],
                "reason": existing["reason"],
            },
            new_values=None,
        )
        connection.execute(
            "DELETE FROM maintenance_blocks WHERE id = ? AND space_id = ?",
            (block_id, space_id),
        )
