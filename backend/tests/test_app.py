import sqlite3

from fastapi.testclient import TestClient

from backend.database import initialize_database
from backend.main import app


EXPECTED_TABLES = {
    "users",
    "spaces",
    "reservations",
    "maintenance_blocks",
    "history_events",
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
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert _schema_tables(connection) == EXPECTED_TABLES
        assert {row[1] for row in connection.execute("PRAGMA table_info(users)")} >= {
            "full_name",
            "institutional_email",
            "identification",
            "password_hash",
            "role",
            "is_active",
        }


def test_migration_updates_preexisting_empty_database(tmp_path, monkeypatch):
    database_path = tmp_path / "existing.sqlite3"
    database_path.touch()
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))

    initialize_database()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
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
