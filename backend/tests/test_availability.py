from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.espacios.service import create_space
from backend.main import app
from backend.reservas.service import create_reservation
from backend.usuarios.service import create_initial_admin


@pytest.fixture
def availability_api(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ACADEMIC_RESERVATIONS_DB_PATH", str(tmp_path / "availability.sqlite3")
    )
    with TestClient(app) as client:
        admin = create_initial_admin(
            full_name="Administradora",
            institutional_email="admin@universidad.edu.co",
            password="abcdefghijkl",
        )
        login = client.post(
            "/auth/login",
            json={
                "institutional_email": "admin@universidad.edu.co",
                "password": "abcdefghijkl",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        space = create_space(
            actor_user_id=admin["id"],
            name="Sala de consulta",
            type="aula",
            capacity=20,
            location="Edificio A",
            equipment=[],
            is_active=True,
            requires_approval=False,
        )
        yield client, headers, admin["id"], space


def _future_interval():
    starts_at = datetime.now(timezone.utc) + timedelta(days=40)
    ends_at = starts_at + timedelta(hours=2)
    return starts_at, ends_at


def _query(client, headers, space_id, starts_at, ends_at):
    return client.get(
        f"/availability/spaces/{space_id}",
        headers=headers,
        params={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )


def _insert_reservation(user_id, space_id, status, starts_at, ends_at):
    with database_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, ?, ?, ?, ?, '2029-01-01T00:00:00+00:00')""",
            (
                user_id,
                space_id,
                starts_at.isoformat(),
                ends_at.isoformat(),
                status,
            ),
        )
        return cursor.lastrowid


def test_unoccupied_interval_is_available(availability_api):
    client, headers, _, space = availability_api
    starts_at, ends_at = _future_interval()

    response = _query(client, headers, space["id"], starts_at, ends_at)

    assert response.status_code == 200
    assert response.json()["availability"] == "available"
    assert response.json()["is_available"] is True


@pytest.mark.parametrize("reservation_status", ["pending", "approved"])
def test_partial_overlap_with_active_reservation_is_occupied(
    availability_api, reservation_status
):
    client, headers, user_id, space = availability_api
    starts_at, _ = _future_interval()
    _insert_reservation(
        user_id,
        space["id"],
        reservation_status,
        starts_at + timedelta(minutes=30),
        starts_at + timedelta(minutes=90),
    )

    response = _query(
        client,
        headers,
        space["id"],
        starts_at + timedelta(hours=1),
        starts_at + timedelta(hours=2),
    )

    assert response.status_code == 200
    assert response.json()["availability"] == "occupied"
    assert response.json()["is_available"] is False


@pytest.mark.parametrize("reservation_status", ["rejected", "cancelled", "finished"])
def test_resolved_reservation_does_not_occupy_interval(
    availability_api, reservation_status
):
    client, headers, user_id, space = availability_api
    starts_at, ends_at = _future_interval()
    _insert_reservation(
        user_id, space["id"], reservation_status, starts_at, ends_at
    )

    response = _query(client, headers, space["id"], starts_at, ends_at)

    assert response.status_code == 200
    assert response.json()["availability"] == "available"


def test_interval_starting_when_reservation_ends_is_available(availability_api):
    client, headers, user_id, space = availability_api
    starts_at, _ = _future_interval()
    reservation_end = starts_at + timedelta(hours=1)
    _insert_reservation(
        user_id,
        space["id"],
        "approved",
        starts_at,
        reservation_end,
    )

    response = _query(
        client,
        headers,
        space["id"],
        reservation_end,
        reservation_end + timedelta(hours=1),
    )

    assert response.json()["availability"] == "available"


def test_partial_overlap_with_maintenance_is_blocked(availability_api):
    client, headers, _, space = availability_api
    starts_at, _ = _future_interval()
    maintenance_start = starts_at + timedelta(minutes=30)
    maintenance_end = starts_at + timedelta(minutes=90)
    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=headers,
        json={
            "starts_at": maintenance_start.isoformat(),
            "ends_at": maintenance_end.isoformat(),
            "reason": "Inspección técnica",
        },
    )
    assert response.status_code == 201

    availability = _query(
        client,
        headers,
        space["id"],
        starts_at + timedelta(hours=1),
        starts_at + timedelta(hours=2),
    )

    assert availability.status_code == 200
    assert availability.json()["availability"] == "blocked"
    assert availability.json()["is_available"] is False


def test_interval_starting_when_maintenance_ends_is_available(availability_api):
    client, headers, _, space = availability_api
    starts_at, _ = _future_interval()
    maintenance_end = starts_at + timedelta(hours=1)
    created = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=headers,
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": maintenance_end.isoformat(),
            "reason": "Inspección técnica",
        },
    )
    assert created.status_code == 201

    response = _query(
        client,
        headers,
        space["id"],
        maintenance_end,
        maintenance_end + timedelta(hours=1),
    )

    assert response.json()["availability"] == "available"


def test_inactive_or_missing_space_cannot_be_reported_as_available(availability_api):
    client, headers, _, space = availability_api
    starts_at, ends_at = _future_interval()
    inactive = client.patch(
        f"/spaces/{space['id']}/status",
        headers=headers,
        json={"is_active": False},
    )

    assert inactive.status_code == 200
    assert _query(client, headers, space["id"], starts_at, ends_at).status_code == 409
    assert _query(client, headers, 9999, starts_at, ends_at).status_code == 404


def test_availability_requires_an_authenticated_user(availability_api):
    client, _, _, space = availability_api
    starts_at, ends_at = _future_interval()

    response = _query(client, {}, space["id"], starts_at, ends_at)

    assert response.status_code == 401


def test_invalid_interval_is_rejected(availability_api):
    client, headers, _, space = availability_api
    starts_at, _ = _future_interval()

    response = _query(
        client,
        headers,
        space["id"],
        starts_at,
        starts_at,
    )

    assert response.status_code == 422
