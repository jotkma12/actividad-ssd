"""Space persistence, bookability checks, and status operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3

from backend.database import database_connection
from backend.historial.records import record_event


class SpaceNotFoundError(Exception):
    """The requested space does not exist."""


class InactiveSpaceError(Exception):
    """The space exists but cannot accept new reservations."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _space_dict(row: sqlite3.Row) -> dict:
    space = dict(row)
    space["equipment"] = json.loads(space.pop("equipment_json"))
    space["is_active"] = bool(space["is_active"])
    space["requires_approval"] = bool(space["requires_approval"])
    return space


def list_spaces() -> list[dict]:
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces ORDER BY name COLLATE NOCASE, id"""
        ).fetchall()
        return [_space_dict(row) for row in rows]


def get_space(space_id: int) -> dict:
    with database_connection() as connection:
        row = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        if row is None:
            raise SpaceNotFoundError
        return _space_dict(row)


def require_active_space(space_id: int) -> dict:
    """Return an active space or reject attempts to book an inactive one."""
    space = get_space(space_id)
    if not space["is_active"]:
        raise InactiveSpaceError("El espacio está desactivado y no acepta reservas nuevas")
    return space


def create_space(*, actor_user_id: int, **values) -> dict:
    equipment = values.pop("equipment")
    now = _utc_now()
    persisted = {
        **values,
        "equipment": equipment,
    }
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """INSERT INTO spaces (
                   name, type, capacity, location, equipment_json, is_active,
                   requires_approval, created_at_utc
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                values["name"],
                values["type"],
                values["capacity"],
                values["location"],
                json.dumps(equipment, ensure_ascii=False),
                int(values["is_active"]),
                int(values["requires_approval"]),
                now,
            ),
        )
        space_id = cursor.lastrowid
        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="space",
            entity_id=space_id,
            action="space_created",
            old_values=None,
            new_values=persisted,
        )
        row = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        return _space_dict(row)


def update_space(*, actor_user_id: int, space_id: int, **values) -> dict:
    equipment = values.pop("equipment")
    next_values = {**values, "equipment": equipment}
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        if row is None:
            raise SpaceNotFoundError
        current = _space_dict(row)
        old_values = {key: current[key] for key in next_values}
        if old_values != next_values:
            connection.execute(
                """UPDATE spaces
                   SET name = ?, type = ?, capacity = ?, location = ?, equipment_json = ?
                   WHERE id = ?""",
                (
                    values["name"],
                    values["type"],
                    values["capacity"],
                    values["location"],
                    json.dumps(equipment, ensure_ascii=False),
                    space_id,
                ),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="space",
                entity_id=space_id,
                action="space_updated",
                old_values=old_values,
                new_values=next_values,
            )
        updated = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        return _space_dict(updated)


def set_space_status(
    *, actor_user_id: int, space_id: int, is_active: bool
) -> tuple[dict, int]:
    now = _utc_now()
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        if row is None:
            raise SpaceNotFoundError

        current = _space_dict(row)
        if current["is_active"] != is_active:
            connection.execute(
                "UPDATE spaces SET is_active = ? WHERE id = ?",
                (int(is_active), space_id),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="space",
                entity_id=space_id,
                action="space_activated" if is_active else "space_deactivated",
                old_values={"is_active": current["is_active"]},
                new_values={"is_active": is_active},
            )

        reservations_to_review = 0
        if not is_active:
            reservations_to_review = connection.execute(
                """SELECT COUNT(*) FROM reservations
                   WHERE space_id = ? AND status IN ('pending', 'approved')
                     AND starts_at_utc > ?""",
                (space_id, now),
            ).fetchone()[0]

        updated = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        return _space_dict(updated), reservations_to_review


def set_space_approval_policy(
    *, actor_user_id: int, space_id: int, requires_approval: bool
) -> dict:
    """Update approval policy for future reservations without changing existing ones."""
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        if row is None:
            raise SpaceNotFoundError
        current = _space_dict(row)
        if current["requires_approval"] != requires_approval:
            connection.execute(
                "UPDATE spaces SET requires_approval = ? WHERE id = ?",
                (int(requires_approval), space_id),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="space",
                entity_id=space_id,
                action="space_approval_policy_updated",
                old_values={"requires_approval": current["requires_approval"]},
                new_values={"requires_approval": requires_approval},
            )
        updated = connection.execute(
            """SELECT id, name, type, capacity, location, equipment_json, is_active,
                      requires_approval, created_at_utc
               FROM spaces WHERE id = ?""",
            (space_id,),
        ).fetchone()
        return _space_dict(updated)
