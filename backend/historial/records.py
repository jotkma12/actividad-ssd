"""Shared writer for immutable audit events emitted by domain modules."""

import json
import sqlite3


def record_event(
    connection: sqlite3.Connection,
    *,
    actor_user_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    old_values: dict | None,
    new_values: dict | None,
) -> None:
    connection.execute(
        """INSERT INTO history_events (
               actor_user_id, occurred_at_utc, entity_type, entity_id, action,
               old_values_json, new_values_json
           ) VALUES (?, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'), ?, ?, ?, ?, ?)""",
        (
            actor_user_id,
            entity_type,
            entity_id,
            action,
            json.dumps(old_values, ensure_ascii=False, sort_keys=True)
            if old_values is not None
            else None,
            json.dumps(new_values, ensure_ascii=False, sort_keys=True)
            if new_values is not None
            else None,
        ),
    )
