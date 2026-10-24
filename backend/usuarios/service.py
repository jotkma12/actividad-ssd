"""Persistence and account lifecycle operations for the users module."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from backend.database import database_connection
from backend.historial.records import record_event
from backend.usuarios.security import (
    create_bearer_token,
    hash_bearer_token,
    hash_password,
    normalize_institutional_email,
    validate_password,
    verify_password,
)


class AccountConflictError(Exception):
    """The requested account operation conflicts with existing data."""


class AccountNotFoundError(Exception):
    """The requested account does not exist."""


class InvalidCredentialsError(Exception):
    """Authentication failed without disclosing which credential was invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_dict(row: sqlite3.Row) -> dict:
    user = dict(row)
    user["is_active"] = bool(user["is_active"])
    return user


def create_account(
    *,
    actor_user_id: int,
    full_name: str,
    institutional_email: str,
    identification: str,
    password: str,
    role: str,
) -> dict:
    full_name = full_name.strip()
    identification = identification.strip()
    email = normalize_institutional_email(institutional_email)
    validate_password(password)
    if not full_name or not identification:
        raise ValueError("El nombre y la identificación son obligatorios")

    encoded_password = hash_password(password)
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = connection.execute(
            "SELECT institutional_email, identification FROM users "
            "WHERE institutional_email = ? OR identification = ?",
            (email, identification),
        ).fetchone()
        if duplicate:
            if duplicate["institutional_email"] == email:
                raise AccountConflictError("El correo institucional ya está registrado")
            raise AccountConflictError("La identificación ya está registrada")

        cursor = connection.execute(
            """INSERT INTO users (
                   full_name, institutional_email, identification, password_hash,
                   role, is_active, created_at_utc
               ) VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (full_name, email, identification, encoded_password, role, _utc_now()),
        )
        row = connection.execute(
            "SELECT id, full_name, institutional_email, identification, role, "
            "is_active, created_at_utc FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="user",
            entity_id=cursor.lastrowid,
            action="user_created",
            old_values=None,
            new_values={
                "full_name": full_name,
                "institutional_email": email,
                "identification": identification,
                "role": role,
                "is_active": False,
            },
        )
        return _user_dict(row)


def create_initial_admin(*, full_name: str, institutional_email: str, password: str) -> dict:
    full_name = full_name.strip()
    email = normalize_institutional_email(institutional_email)
    validate_password(password)
    if not full_name:
        raise ValueError("El nombre completo es obligatorio")

    encoded_password = hash_password(password)
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM users WHERE role = 'administrator' LIMIT 1"
        ).fetchone():
            raise AccountConflictError("Ya existe un administrador; no se creó otro")
        if connection.execute(
            "SELECT 1 FROM users WHERE institutional_email = ?", (email,)
        ).fetchone():
            raise AccountConflictError("El correo institucional ya está registrado")

        cursor = connection.execute(
            """INSERT INTO users (
                   full_name, institutional_email, identification, password_hash,
                   role, is_active, created_at_utc
               ) VALUES (?, ?, NULL, ?, 'administrator', 1, ?)""",
            (full_name, email, encoded_password, _utc_now()),
        )
        row = connection.execute(
            "SELECT id, full_name, institutional_email, identification, role, "
            "is_active, created_at_utc FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        record_event(
            connection,
            actor_user_id=None,
            entity_type="user",
            entity_id=cursor.lastrowid,
            action="initial_administrator_created",
            old_values=None,
            new_values={
                "full_name": full_name,
                "institutional_email": email,
                "role": "administrator",
                "is_active": True,
            },
        )
        return _user_dict(row)


def authenticate(institutional_email: str, password: str) -> tuple[str, dict]:
    email = normalize_institutional_email(institutional_email)
    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE institutional_email = ?", (email,)
        ).fetchone()
        if row is None or not row["is_active"] or not verify_password(
            password, row["password_hash"]
        ):
            raise InvalidCredentialsError

        token = create_bearer_token()
        connection.execute(
            "INSERT INTO user_sessions (token_hash, user_id, created_at_utc) VALUES (?, ?, ?)",
            (hash_bearer_token(token), row["id"], _utc_now()),
        )
        return token, _user_dict(row)


def get_user_for_session(token: str) -> dict | None:
    with database_connection() as connection:
        row = connection.execute(
            """SELECT users.id, users.full_name, users.institutional_email,
                      users.identification, users.role, users.is_active,
                      users.created_at_utc
               FROM user_sessions
               JOIN users ON users.id = user_sessions.user_id
               WHERE user_sessions.token_hash = ? AND users.is_active = 1""",
            (hash_bearer_token(token),),
        ).fetchone()
        return _user_dict(row) if row else None


def revoke_session(token: str) -> None:
    with database_connection() as connection:
        connection.execute(
            "DELETE FROM user_sessions WHERE token_hash = ?",
            (hash_bearer_token(token),),
        )


def list_accounts() -> list[dict]:
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT id, full_name, institutional_email, identification, role,
                      is_active, created_at_utc
               FROM users ORDER BY id"""
        ).fetchall()
        return [_user_dict(row) for row in rows]


def update_account_profile(
    user_id: int,
    *,
    actor_user_id: int,
    full_name: str,
    institutional_email: str,
    identification: str,
) -> dict:
    full_name = full_name.strip()
    identification = identification.strip()
    email = normalize_institutional_email(institutional_email)
    if not full_name or not identification:
        raise ValueError("El nombre y la identificación son obligatorios")

    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current_row = connection.execute(
            """SELECT id, full_name, institutional_email, identification, role,
                      is_active, created_at_utc
               FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
        if current_row is None:
            raise AccountNotFoundError

        duplicate = connection.execute(
            """SELECT institutional_email, identification FROM users
               WHERE id != ? AND (institutional_email = ? OR identification = ?)""",
            (user_id, email, identification),
        ).fetchone()
        if duplicate:
            if duplicate["institutional_email"] == email:
                raise AccountConflictError("El correo institucional ya está registrado")
            raise AccountConflictError("La identificación ya está registrada")

        current = _user_dict(current_row)
        old_values = {
            "full_name": current["full_name"],
            "institutional_email": current["institutional_email"],
            "identification": current["identification"],
        }
        new_values = {
            "full_name": full_name,
            "institutional_email": email,
            "identification": identification,
        }
        if old_values != new_values:
            connection.execute(
                """UPDATE users
                   SET full_name = ?, institutional_email = ?, identification = ?
                   WHERE id = ?""",
                (full_name, email, identification, user_id),
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="user",
                entity_id=user_id,
                action="user_profile_updated",
                old_values=old_values,
                new_values=new_values,
            )
        updated = connection.execute(
            """SELECT id, full_name, institutional_email, identification, role,
                      is_active, created_at_utc
               FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
        return _user_dict(updated)


def list_space_approvers(space_id: int) -> list[dict]:
    with database_connection() as connection:
        if connection.execute(
            "SELECT 1 FROM spaces WHERE id = ?", (space_id,)
        ).fetchone() is None:
            raise AccountNotFoundError("El espacio no existe")
        rows = connection.execute(
            """SELECT u.id, u.full_name, u.institutional_email, u.identification,
                      u.role, u.is_active, u.created_at_utc
               FROM space_approvers AS sa
               JOIN users AS u ON u.id = sa.approver_user_id
               WHERE sa.space_id = ? ORDER BY u.full_name COLLATE NOCASE, u.id""",
            (space_id,),
        ).fetchall()
        return [_user_dict(row) for row in rows]


def set_account_status(
    user_id: int, is_active: bool, *, actor_user_id: int
) -> tuple[dict, int]:
    now = _utc_now()
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT id, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise AccountNotFoundError

        if bool(row["is_active"]) != is_active:
            connection.execute(
                "UPDATE users SET is_active = ? WHERE id = ?", (int(is_active), user_id)
            )
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="user",
                entity_id=user_id,
                action="user_activated" if is_active else "user_deactivated",
                old_values={"is_active": bool(row["is_active"])},
                new_values={"is_active": is_active},
            )
        if not is_active:
            connection.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))

        future_reservations = 0
        if not is_active:
            future_reservations = connection.execute(
                """SELECT COUNT(*) FROM reservations
                   WHERE user_id = ? AND status IN ('pending', 'approved')
                     AND starts_at_utc > ?""",
                (user_id, now),
            ).fetchone()[0]

        updated = connection.execute(
            """SELECT id, full_name, institutional_email, identification, role,
                      is_active, created_at_utc FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
        return _user_dict(updated), future_reservations


def set_account_role(user_id: int, role: str, *, actor_user_id: int) -> dict:
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if current is None:
            raise AccountNotFoundError
        cursor = connection.execute(
            "UPDATE users SET role = ? WHERE id = ?", (role, user_id)
        )
        if cursor.rowcount == 0:
            raise AccountNotFoundError
        if current["role"] != role:
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="user",
                entity_id=user_id,
                action="user_role_changed",
                old_values={"role": current["role"]},
                new_values={"role": role},
            )
        row = connection.execute(
            """SELECT id, full_name, institutional_email, identification, role,
                      is_active, created_at_utc FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
        return _user_dict(row)


def assign_approver(
    space_id: int, approver_user_id: int, *, actor_user_id: int
) -> None:
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        space = connection.execute(
            "SELECT 1 FROM spaces WHERE id = ?", (space_id,)
        ).fetchone()
        if space is None:
            raise AccountNotFoundError("El espacio no existe")
        approver = connection.execute(
            "SELECT role FROM users WHERE id = ?", (approver_user_id,)
        ).fetchone()
        if approver is None:
            raise AccountNotFoundError("La cuenta no existe")
        if approver["role"] != "approver":
            raise ValueError("La cuenta debe tener el rol de aprobador")
        cursor = connection.execute(
            """INSERT INTO space_approvers (space_id, approver_user_id, assigned_at_utc)
               VALUES (?, ?, ?)
               ON CONFLICT (space_id, approver_user_id) DO NOTHING""",
            (space_id, approver_user_id, _utc_now()),
        )
        if cursor.rowcount:
            record_event(
                connection,
                actor_user_id=actor_user_id,
                entity_type="space",
                entity_id=space_id,
                action="space_approver_assigned",
                old_values=None,
                new_values={"approver_user_id": approver_user_id},
            )


def remove_approver(
    space_id: int, approver_user_id: int, *, actor_user_id: int
) -> None:
    with database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            "DELETE FROM space_approvers WHERE space_id = ? AND approver_user_id = ?",
            (space_id, approver_user_id),
        )
        if cursor.rowcount == 0:
            raise AccountNotFoundError("La asignación no existe")
        record_event(
            connection,
            actor_user_id=actor_user_id,
            entity_type="space",
            entity_id=space_id,
            action="space_approver_removed",
            old_values={"approver_user_id": approver_user_id},
            new_values=None,
        )


def get_approver_space_ids(approver_user_id: int) -> set[int]:
    with database_connection() as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT space_id FROM space_approvers WHERE approver_user_id = ?",
                (approver_user_id,),
            )
        }
