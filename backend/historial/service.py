"""Permission-scoped, read-only access to audit events."""

from __future__ import annotations

import json
import sqlite3

from backend.database import database_connection
from backend.usuarios.permissions import Principal


class HistoryNotFoundError(Exception):
    """The entity is missing or outside the caller's history scope."""


class InvalidHistoryFilterError(Exception):
    """The requested history filter is not supported."""


ENTITY_TYPES = {"user", "space", "reservation", "maintenance_block"}


def _assert_entity_visible(
    connection: sqlite3.Connection,
    *,
    principal: Principal,
    entity_type: str,
    entity_id: int,
) -> None:
    if entity_type not in ENTITY_TYPES:
        raise HistoryNotFoundError
    if principal.role == "administrator":
        table = {
            "user": "users",
            "space": "spaces",
            "reservation": "reservations",
            "maintenance_block": "maintenance_blocks",
        }[entity_type]
        if connection.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (entity_id,)
        ).fetchone() or connection.execute(
            "SELECT 1 FROM history_events WHERE entity_type = ? AND entity_id = ? LIMIT 1",
            (entity_type, entity_id),
        ).fetchone():
            return
        raise HistoryNotFoundError

    if principal.role == "requester" and entity_type == "reservation":
        row = connection.execute(
            "SELECT user_id FROM reservations WHERE id = ?", (entity_id,)
        ).fetchone()
        if row is not None and row["user_id"] == principal.user_id:
            return
        raise HistoryNotFoundError

    if principal.role == "approver":
        if entity_type == "reservation":
            row = connection.execute(
                "SELECT space_id FROM reservations WHERE id = ?", (entity_id,)
            ).fetchone()
        elif entity_type == "space":
            row = connection.execute(
                "SELECT id AS space_id FROM spaces WHERE id = ?", (entity_id,)
            ).fetchone()
        elif entity_type == "maintenance_block":
            row = connection.execute(
                "SELECT space_id FROM maintenance_blocks WHERE id = ?", (entity_id,)
            ).fetchone()
            if row is None:
                events = connection.execute(
                    """SELECT old_values_json, new_values_json FROM history_events
                       WHERE entity_type = 'maintenance_block' AND entity_id = ?""",
                    (entity_id,),
                ).fetchall()
                space_id = None
                for event in events:
                    for values in (event["old_values_json"], event["new_values_json"]):
                        if values:
                            space_id = json.loads(values).get("space_id")
                            if space_id is not None:
                                break
                    if space_id is not None:
                        break
                row = {"space_id": space_id} if space_id is not None else None
        else:
            row = None
        if row is not None and connection.execute(
            """SELECT 1 FROM space_approvers
               WHERE space_id = ? AND approver_user_id = ?""",
            (row["space_id"], principal.user_id),
        ).fetchone():
            return
    raise HistoryNotFoundError


def _event_dict(row: sqlite3.Row) -> dict:
    event = dict(row)
    for key in ("old_values_json", "new_values_json"):
        value = event.pop(key)
        event[key.removesuffix("_json")] = json.loads(value) if value else None
    return event


def list_history(
    *,
    principal: Principal,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> list[dict]:
    if not principal.is_active:
        raise HistoryNotFoundError
    if entity_type is not None and entity_type not in ENTITY_TYPES:
        raise InvalidHistoryFilterError
    if entity_id is not None and entity_type is None:
        raise InvalidHistoryFilterError

    with database_connection() as connection:
        if entity_id is not None:
            _assert_entity_visible(
                connection,
                principal=principal,
                entity_type=entity_type,
                entity_id=entity_id,
            )

        clauses: list[str] = []
        parameters: list[object] = []
        if entity_id is None and principal.role == "requester":
            clauses.append(
                "entity_type = 'reservation' AND entity_id IN "
                "(SELECT id FROM reservations WHERE user_id = ?)"
            )
            parameters.append(principal.user_id)
        elif entity_id is None and principal.role == "approver":
            clauses.append(
                "((entity_type = 'reservation' AND entity_id IN "
                "(SELECT r.id FROM reservations AS r JOIN space_approvers AS sa "
                "ON sa.space_id = r.space_id WHERE sa.approver_user_id = ?)) "
                "OR (entity_type = 'space' AND entity_id IN "
                "(SELECT space_id FROM space_approvers WHERE approver_user_id = ?)) "
                "OR (entity_type = 'maintenance_block' AND entity_id IN "
                "(SELECT mb.id FROM maintenance_blocks AS mb JOIN space_approvers AS sa "
                "ON sa.space_id = mb.space_id WHERE sa.approver_user_id = ?)))"
            )
            parameters.extend([principal.user_id] * 3)
        if entity_type is not None:
            clauses.append("entity_type = ?")
            parameters.append(entity_type)
        if entity_id is not None:
            clauses.append("entity_id = ?")
            parameters.append(entity_id)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = connection.execute(
            """SELECT h.id, h.actor_user_id, u.full_name AS actor_full_name,
                      u.role AS actor_role, h.occurred_at_utc, h.entity_type,
                      h.entity_id, h.action, h.old_values_json, h.new_values_json,
                      h.reason
               FROM history_events AS h
               LEFT JOIN users AS u ON u.id = h.actor_user_id"""
            + where
            + " ORDER BY h.occurred_at_utc ASC, h.id ASC",
            parameters,
        ).fetchall()
        return [_event_dict(row) for row in rows]
