"""Configuración inicial de SQLite para desarrollo local."""

import os
import sqlite3
from pathlib import Path

from backend.migrations import apply_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / ".local" / "academic_reservations.sqlite3"
DATABASE_PATH_ENV = "ACADEMIC_RESERVATIONS_DB_PATH"


def get_database_path() -> Path:
    """Return the configured database path or the local development default."""
    configured_path = os.getenv(DATABASE_PATH_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH


def initialize_database() -> Path:
    """Create the SQLite file and apply pending versioned schema changes."""
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        apply_migrations(connection)

    return database_path
