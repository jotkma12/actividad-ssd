import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import initialize_database
from backend.main import app


EXPECTED_TABLES = {
    "users",
    "spaces",
    "reservations",
    "maintenance_blocks",
    "history_events",
    "user_sessions",
    "space_approvers",
}


def _schema_tables(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def test_startup_migrates_empty_sqlite_database(tmp_path, monkeypatch):
    database_path = tmp_path / "data" / "reservations.sqlite3"
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert database_path.is_file()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert _schema_tables(connection) == EXPECTED_TABLES
        assert {row[1] for row in connection.execute("PRAGMA table_info(users)")} >= {
            "full_name",
            "institutional_email",
            "identification",
            "password_hash",
            "role",
            "is_active",
        }
        assert "cancellation_reason" in {
            row[1] for row in connection.execute("PRAGMA table_info(reservations)")
        }


def test_migration_updates_preexisting_empty_database(tmp_path, monkeypatch):
    database_path = tmp_path / "existing.sqlite3"
    database_path.touch()
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))

    initialize_database()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert _schema_tables(connection) == EXPECTED_TABLES


def test_migration_is_idempotent_after_schema_is_current(tmp_path, monkeypatch):
    database_path = tmp_path / "reservations.sqlite3"
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))

    initialize_database()
    with sqlite3.connect(database_path) as connection:
        tables_before = _schema_tables(connection)
        version_before = connection.execute("PRAGMA user_version").fetchone()[0]

    initialize_database()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == version_before
        assert _schema_tables(connection) == tables_before


def test_user_migration_preserves_existing_reservation_references(tmp_path, monkeypatch):
    database_path = tmp_path / "version_one.sqlite3"
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))
    migration_v1 = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "0001_initial_schema.sql"
    ).read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(migration_v1)
        connection.execute(
            """INSERT INTO users (
                   id, full_name, institutional_email, identification, password_hash,
                   role, is_active, created_at_utc
               ) VALUES (1, 'Admin', 'admin@universidad.edu.co', 'A-1', 'hash',
                         'administrator', 1, '2026-01-01T00:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO spaces (
                   id, name, type, capacity, location, requires_approval, created_at_utc
               ) VALUES (1, 'Sala', 'aula', 10, 'Edificio A', 0, '2026-01-01T00:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO reservations (
                   id, user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (1, 1, 1, '2026-02-01T08:00:00+00:00',
                         '2026-02-01T09:00:00+00:00', 'approved',
                         '2026-01-01T00:00:00+00:00')"""
        )
        connection.execute("PRAGMA user_version = 1")

    initialize_database()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute(
            "SELECT institutional_email, identification FROM users WHERE id = 1"
        ).fetchone() == ("admin@universidad.edu.co", "A-1")
        assert connection.execute(
            "SELECT user_id FROM reservations WHERE id = 1"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT cancellation_reason FROM reservations WHERE id = 1"
        ).fetchone() == (None,)
        assert "cancellation_reason" in {
            row[1] for row in connection.execute("PRAGMA table_info(reservations)")
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
