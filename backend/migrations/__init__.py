"""SQLite schema migration runner."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).with_name("versions")
MIGRATION_FILENAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def _migration_files() -> list[tuple[int, Path]]:
    migrations = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Nombre de migración inválido: {path.name}")
        migrations.append((int(match.group(1)), path))

    migrations.sort(key=lambda item: item[0])
    versions = [version for version, _ in migrations]
    if len(versions) != len(set(versions)):
        raise ValueError("Hay versiones de migración duplicadas")
    if versions and versions != list(range(1, versions[-1] + 1)):
        raise ValueError("Las versiones de migración deben ser consecutivas desde 0001")
    return migrations


def _execute_sql_statements(connection: sqlite3.Connection, sql: str) -> None:
    pending = ""
    for line in sql.splitlines():
        pending += line + "\n"
        if sqlite3.complete_statement(pending):
            if pending.strip():
                connection.execute(pending)
            pending = ""
    if pending.strip():
        raise ValueError("La migración termina con una sentencia SQL incompleta")


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply each unapplied SQL migration in its own SQLite transaction."""
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    migrations = _migration_files()
    latest_version = migrations[-1][0] if migrations else 0
    if current_version > latest_version:
        raise RuntimeError(
            f"La base usa la versión {current_version}, superior a la disponible "
            f"({latest_version})"
        )

    for version, path in migrations:
        if version <= current_version:
            continue
        if connection.in_transaction:
            raise RuntimeError("Las migraciones requieren una conexión sin transacción activa")

        sql = path.read_text(encoding="utf-8")
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        try:
            _execute_sql_statements(connection, sql)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise sqlite3.IntegrityError(
                    f"La migración {path.name} dejaría relaciones inválidas: {violations}"
                )
            connection.execute(f"PRAGMA user_version = {version}")
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.execute(
                f"PRAGMA foreign_keys = {1 if foreign_keys_enabled else 0}"
            )
        current_version = version

    return current_version
