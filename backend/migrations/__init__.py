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

        sql = path.read_text(encoding="utf-8")
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{sql}\n"
            f"PRAGMA user_version = {version};\n"
            "COMMIT;"
        )
        try:
            connection.executescript(script)
        except sqlite3.Error:
            if connection.in_transaction:
                connection.rollback()
            raise
        current_version = version

    return current_version
