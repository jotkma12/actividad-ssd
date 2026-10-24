import json

import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.espacios.service import InactiveSpaceError, require_active_space
from backend.main import app
from backend.usuarios.service import create_initial_admin


@pytest.fixture
def space_api(tmp_path, monkeypatch):
    database_path = tmp_path / "spaces.sqlite3"
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))
    with TestClient(app) as client:
        create_initial_admin(
            full_name="Administradora",
            institutional_email="admin@universidad.edu.co",
            password="abcdefghijkl",
        )
        response = client.post(
            "/auth/login",
            json={
                "institutional_email": "admin@universidad.edu.co",
                "password": "abcdefghijkl",
            },
        )
        admin_headers = {
            "Authorization": f"Bearer {response.json()['access_token']}"
        }
        yield client, admin_headers


def _space_payload(**overrides):
    payload = {
        "name": "Laboratorio de física",
        "type": "laboratorio",
        "capacity": 24,
        "location": "Edificio A, piso 2",
        "equipment": ["Proyector", "Microscopios"],
        "is_active": True,
        "requires_approval": True,
    }
    payload.update(overrides)
    return payload


def _create_space(client, admin_headers):
    response = client.post(
        "/spaces", headers=admin_headers, json=_space_payload()
    )
    assert response.status_code == 201
    return response.json()


def _insert_reservation(space_id, status, starts_at, ends_at):
    with database_connection() as connection:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE role = 'administrator'"
        ).fetchone()[0]
        cursor = connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, ?, ?, ?, ?, '2029-01-01T00:00:00.000000+00:00')""",
            (admin_id, space_id, starts_at, ends_at, status),
        )
        return cursor.lastrowid


def test_administrator_creates_and_people_can_query_spaces(space_api):
    client, admin_headers = space_api
    response = client.post(
        "/spaces", headers=admin_headers, json=_space_payload()
    )

    assert response.status_code == 201
    space = response.json()
    assert space["name"] == "Laboratorio de física"
    assert space["capacity"] == 24
    assert space["equipment"] == ["Proyector", "Microscopios"]
    assert space["is_active"] is True
    assert space["requires_approval"] is True
    assert client.get("/spaces").json() == [space]
    assert client.get(f"/spaces/{space['id']}").json() == space

    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, new_values_json FROM history_events
               WHERE entity_type = 'space' AND entity_id = ?""",
            (space["id"],),
        ).fetchone()
    assert event["action"] == "space_created"
    assert json.loads(event["new_values_json"])["name"] == "Laboratorio de física"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"type": ""},
        {"capacity": 0},
        {"capacity": -1},
        {"location": "  "},
        {"equipment": [""]},
    ],
)
def test_invalid_space_data_is_rejected(space_api, overrides):
    client, admin_headers = space_api

    response = client.post(
        "/spaces", headers=admin_headers, json=_space_payload(**overrides)
    )

    assert response.status_code == 422
    assert client.get("/spaces").json() == []


def test_space_management_requires_an_administrator(space_api):
    client, admin_headers = space_api
    account = client.post(
        "/users",
        headers=admin_headers,
        json={
            "full_name": "Solicitante",
            "institutional_email": "solicitante@universidad.edu.co",
            "identification": "SOL-1",
            "password": "una-clave-larga",
            "role": "requester",
        },
    ).json()
    client.patch(
        f"/users/{account['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    login = client.post(
        "/auth/login",
        json={
            "institutional_email": "solicitante@universidad.edu.co",
            "password": "una-clave-larga",
        },
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.post("/spaces", headers=user_headers, json=_space_payload()).status_code == 403
    assert client.put(
        "/spaces/1", headers=user_headers, json=_space_payload()
    ).status_code == 403
    assert client.patch(
        "/spaces/1/status", headers=user_headers, json={"is_active": False}
    ).status_code == 403


def test_administrator_edits_descriptive_space_data_and_records_history(space_api):
    client, admin_headers = space_api
    space = client.post(
        "/spaces", headers=admin_headers, json=_space_payload()
    ).json()

    response = client.put(
        f"/spaces/{space['id']}",
        headers=admin_headers,
        json=_space_payload(
            name="Laboratorio actualizado",
            capacity=30,
            equipment=["Mesas de laboratorio"],
        ),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Laboratorio actualizado"
    assert response.json()["capacity"] == 30
    assert response.json()["requires_approval"] is True
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, old_values_json, new_values_json FROM history_events
               WHERE entity_type = 'space' AND entity_id = ?
               ORDER BY id DESC LIMIT 1""",
            (space["id"],),
        ).fetchone()
    assert event["action"] == "space_updated"
    assert json.loads(event["old_values_json"])["name"] == "Laboratorio de física"
    assert json.loads(event["new_values_json"])["name"] == "Laboratorio actualizado"


def test_deactivation_preserves_future_reservations_and_blocks_bookability(space_api):
    client, admin_headers = space_api
    space = client.post(
        "/spaces", headers=admin_headers, json=_space_payload()
    ).json()
    with database_connection() as connection:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE role = 'administrator'"
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, ?, '2099-01-01T08:00:00+00:00',
                         '2099-01-01T09:00:00+00:00', 'approved',
                         '2098-01-01T00:00:00+00:00')""",
            (admin_id, space["id"]),
        )
        connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, ?, '2099-01-01T10:00:00+00:00',
                         '2099-01-01T11:00:00+00:00', 'pending',
                         '2098-01-01T00:00:00+00:00')""",
            (admin_id, space["id"]),
        )

    response = client.patch(
        f"/spaces/{space['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["space"]["is_active"] is False
    assert response.json()["future_reservations_to_review"] == 2
    with pytest.raises(InactiveSpaceError):
        require_active_space(space["id"])
    assert client.get(f"/spaces/{space['id']}").json()["is_active"] is False
    with database_connection() as connection:
        reservations = connection.execute(
            "SELECT status FROM reservations WHERE space_id = ? ORDER BY id",
            (space["id"],),
        ).fetchall()
        events = connection.execute(
            """SELECT action FROM history_events
               WHERE entity_type = 'space' AND entity_id = ? ORDER BY id""",
            (space["id"],),
        ).fetchall()
    assert [reservation["status"] for reservation in reservations] == [
        "approved",
        "pending",
    ]
    assert [event["action"] for event in events] == [
        "space_created",
        "space_deactivated",
    ]


def test_active_space_passes_bookability_guard(space_api):
    client, admin_headers = space_api
    space = client.post(
        "/spaces", headers=admin_headers, json=_space_payload()
    ).json()

    assert require_active_space(space["id"])["is_active"] is True


def test_administrator_creates_maintenance_block_and_records_history(space_api):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)

    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "Mantenimiento eléctrico",
        },
    )

    assert response.status_code == 201
    block = response.json()
    assert block["starts_at_utc"] == "2030-01-01T13:00:00.000000+00:00"
    assert block["ends_at_utc"] == "2030-01-01T14:00:00.000000+00:00"
    assert client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=admin_headers
    ).json() == [block]
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, new_values_json FROM history_events
               WHERE entity_type = 'maintenance_block' AND entity_id = ?""",
            (block["id"],),
        ).fetchone()
    assert event["action"] == "maintenance_block_created"
    assert json.loads(event["new_values_json"])["reason"] == "Mantenimiento eléctrico"


@pytest.mark.parametrize("reservation_status", ["pending", "approved"])
def test_maintenance_creation_rejects_active_reservation_conflicts(
    space_api, reservation_status
):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    reservation_id = _insert_reservation(
        space["id"],
        reservation_status,
        "2030-01-01T13:30:00.000000+00:00",
        "2030-01-01T14:30:00.000000+00:00",
    )

    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:45:00-05:00",
            "ends_at": "2030-01-01T09:15:00-05:00",
            "reason": "Trabajo urgente",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["reservations"] == [
        {"id": reservation_id, "status": reservation_status}
    ]
    assert client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=admin_headers
    ).json() == []


@pytest.mark.parametrize("reservation_status", ["rejected", "cancelled", "finished"])
def test_resolved_reservations_do_not_block_maintenance(space_api, reservation_status):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    _insert_reservation(
        space["id"],
        reservation_status,
        "2030-01-01T13:30:00.000000+00:00",
        "2030-01-01T14:30:00.000000+00:00",
    )

    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:45:00-05:00",
            "ends_at": "2030-01-01T09:15:00-05:00",
            "reason": "Trabajo programado",
        },
    )

    assert response.status_code == 201


def test_consecutive_reservation_and_maintenance_intervals_do_not_conflict(space_api):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    _insert_reservation(
        space["id"],
        "approved",
        "2030-01-01T13:00:00.000000+00:00",
        "2030-01-01T14:00:00.000000+00:00",
    )

    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T09:00:00-05:00",
            "ends_at": "2030-01-01T10:00:00-05:00",
            "reason": "Mantenimiento después de la reserva",
        },
    )

    assert response.status_code == 201


@pytest.mark.parametrize("reservation_status", ["pending", "approved"])
def test_maintenance_update_with_conflict_keeps_previous_block(
    space_api, reservation_status
):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    block = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "Bloqueo original",
        },
    ).json()
    reservation_id = _insert_reservation(
        space["id"],
        reservation_status,
        "2030-01-01T14:00:00.000000+00:00",
        "2030-01-01T15:00:00.000000+00:00",
    )

    response = client.put(
        f"/spaces/{space['id']}/maintenance-blocks/{block['id']}",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:30:00-05:00",
            "ends_at": "2030-01-01T09:30:00-05:00",
            "reason": "Cambio en conflicto",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["reservations"][0]["id"] == reservation_id
    blocks = client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=admin_headers
    ).json()
    assert blocks == [block]


def test_maintenance_update_succeeds_after_reservation_is_resolved(space_api):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    block = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "Bloqueo original",
        },
    ).json()
    reservation_id = _insert_reservation(
        space["id"],
        "pending",
        "2030-01-01T14:00:00.000000+00:00",
        "2030-01-01T15:00:00.000000+00:00",
    )
    with database_connection() as connection:
        connection.execute(
            "UPDATE reservations SET status = 'cancelled' WHERE id = ?",
            (reservation_id,),
        )

    response = client.put(
        f"/spaces/{space['id']}/maintenance-blocks/{block['id']}",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:30:00-05:00",
            "ends_at": "2030-01-01T09:30:00-05:00",
            "reason": "Bloqueo actualizado",
        },
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "Bloqueo actualizado"
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, old_values_json, new_values_json FROM history_events
               WHERE entity_type = 'maintenance_block' AND entity_id = ?
               ORDER BY id DESC LIMIT 1""",
            (block["id"],),
        ).fetchone()
    assert event["action"] == "maintenance_block_updated"
    assert json.loads(event["old_values_json"])["reason"] == "Bloqueo original"
    assert json.loads(event["new_values_json"])["reason"] == "Bloqueo actualizado"


@pytest.mark.parametrize(
    "payload",
    [
        {"starts_at": "2030-01-01T09:00:00-05:00", "ends_at": "2030-01-01T09:00:00-05:00", "reason": "Mantenimiento"},
        {"starts_at": "2030-01-01T10:00:00-05:00", "ends_at": "2030-01-01T09:00:00-05:00", "reason": "Mantenimiento"},
        {"starts_at": "2030-01-01T08:00:00-05:00", "ends_at": "2030-01-01T09:00:00-05:00", "reason": "  "},
    ],
)
def test_invalid_maintenance_interval_or_reason_is_rejected(space_api, payload):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)

    response = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 422
    assert client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=admin_headers
    ).json() == []


def test_non_admin_cannot_query_or_change_maintenance_blocks(space_api):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    block = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "Bloqueo original",
        },
    ).json()
    account = client.post(
        "/users",
        headers=admin_headers,
        json={
            "full_name": "Solicitante",
            "institutional_email": "solicitante@universidad.edu.co",
            "identification": "SOL-1",
            "password": "una-clave-larga",
            "role": "requester",
        },
    ).json()
    client.patch(
        f"/users/{account['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    login = client.post(
        "/auth/login",
        json={
            "institutional_email": "solicitante@universidad.edu.co",
            "password": "una-clave-larga",
        },
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=user_headers
    ).status_code == 403
    assert client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=user_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "No autorizado",
        },
    ).status_code == 403
    assert client.put(
        f"/spaces/{space['id']}/maintenance-blocks/{block['id']}",
        headers=user_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "No autorizado",
        },
    ).status_code == 403
    assert client.delete(
        f"/spaces/{space['id']}/maintenance-blocks/{block['id']}",
        headers=user_headers,
    ).status_code == 403


def test_administrator_can_remove_maintenance_block_and_history_remains(space_api):
    client, admin_headers = space_api
    space = _create_space(client, admin_headers)
    block = client.post(
        f"/spaces/{space['id']}/maintenance-blocks",
        headers=admin_headers,
        json={
            "starts_at": "2030-01-01T08:00:00-05:00",
            "ends_at": "2030-01-01T09:00:00-05:00",
            "reason": "Bloqueo a retirar",
        },
    ).json()

    response = client.delete(
        f"/spaces/{space['id']}/maintenance-blocks/{block['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 204
    assert client.get(
        f"/spaces/{space['id']}/maintenance-blocks", headers=admin_headers
    ).json() == []
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, old_values_json FROM history_events
               WHERE entity_type = 'maintenance_block' AND entity_id = ?
               ORDER BY id DESC LIMIT 1""",
            (block["id"],),
        ).fetchone()
    assert event["action"] == "maintenance_block_deleted"
    assert json.loads(event["old_values_json"])["reason"] == "Bloqueo a retirar"
