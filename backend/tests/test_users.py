import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.main import app
from backend.usuarios.bootstrap_admin import main as bootstrap_admin
from backend.usuarios.permissions import (
    Principal,
    can_administer,
    can_change_reservation,
    can_decide_reservation,
    can_view_reservation,
)
from backend.usuarios.security import hash_password, verify_password
from backend.usuarios.service import create_initial_admin
from backend.usuarios.service import get_approver_space_ids


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "reservations.sqlite3"
    monkeypatch.setenv("ACADEMIC_RESERVATIONS_DB_PATH", str(database_path))
    with TestClient(app) as test_client:
        yield test_client


def _bootstrap_admin(client):
    create_initial_admin(
        full_name="Administradora Inicial",
        institutional_email="admin@universidad.edu.co",
        password="abcdefghijkl",
    )
    response = client.post(
        "/auth/login",
        json={
            "institutional_email": "ADMIN@universidad.edu.co",
            "password": "abcdefghijkl",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_account(client, admin_headers, **overrides):
    payload = {
        "full_name": "Docente de Prueba",
        "institutional_email": "docente@universidad.edu.co",
        "identification": "DOC-001",
        "password": "una-clave-larga",
        "role": "requester",
    }
    payload.update(overrides)
    return client.post("/users", headers=admin_headers, json=payload)


def _login(client, email, password):
    return client.post(
        "/auth/login",
        json={"institutional_email": email, "password": password},
    )


def test_initial_admin_configuration_creates_one_active_account(client, monkeypatch):
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    answers = iter(
        [
            "Administradora Inicial",
            "admin@universidad.edu.co",
            "Administradora Inicial",
            "admin@universidad.edu.co",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        "backend.usuarios.bootstrap_admin.getpass", lambda _prompt: "abcdefghijkl"
    )

    assert bootstrap_admin() == 0
    assert bootstrap_admin() == 1

    with database_connection() as connection:
        administrators = connection.execute(
            "SELECT role, is_active, identification FROM users"
        ).fetchall()
    assert len(administrators) == 1
    assert tuple(administrators[0]) == ("administrator", 1, None)


@pytest.mark.parametrize(
    ("full_name", "email", "password"),
    [
        ("", "admin@universidad.edu.co", "abcdefghijkl"),
        ("Administradora", "", "abcdefghijkl"),
        ("Administradora", "admin@otro.edu.co", "abcdefghijkl"),
        ("Administradora", "admin@@universidad.edu.co", "abcdefghijkl"),
        ("Administradora", "admin@universidad.edu.co", "corta"),
        ("Administradora", "admin@universidad.edu.co", ""),
    ],
)
def test_initial_admin_rejects_invalid_configuration(
    client, full_name, email, password
):
    with pytest.raises(ValueError):
        create_initial_admin(
            full_name=full_name,
            institutional_email=email,
            password=password,
        )

    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_password_hash_is_salted_and_verifiable():
    first_hash = hash_password("abcdefghijkl")
    second_hash = hash_password("abcdefghijkl")

    assert first_hash != second_hash
    assert verify_password("abcdefghijkl", first_hash)
    assert not verify_password("wrong-password", first_hash)
    assert not verify_password("short", first_hash)


def test_admin_can_create_inactive_account_and_only_hash_is_persisted(client):
    admin_headers = _bootstrap_admin(client)

    response = _create_account(client, admin_headers)

    assert response.status_code == 201
    account = response.json()
    assert account["role"] == "requester"
    assert account["is_active"] is False
    assert "password_hash" not in account
    assert _login(client, "docente@universidad.edu.co", "una-clave-larga").status_code == 401
    assert _login(client, "docente@universidad.edu.co", "wrong-password").status_code == 401
    with database_connection() as connection:
        stored_hash = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?", (account["id"],)
        ).fetchone()[0]
    assert stored_hash != "una-clave-larga"
    assert verify_password("una-clave-larga", stored_hash)


def test_admin_account_creation_rejects_public_users_and_invalid_data(client):
    assert _create_account(client, {}).status_code == 401
    admin_headers = _bootstrap_admin(client)

    assert _create_account(
        client, admin_headers, institutional_email="persona@otro.edu.co"
    ).status_code == 422
    assert _create_account(client, admin_headers, password="corta").status_code == 422
    assert _create_account(
        client,
        admin_headers,
        full_name="",
        institutional_email="otra@universidad.edu.co",
        identification="DOC-002",
    ).status_code == 422
    incomplete = {
        "full_name": "Persona",
        "institutional_email": "persona@universidad.edu.co",
        "identification": "DOC-003",
        "role": "requester",
    }
    assert client.post("/users", headers=admin_headers, json=incomplete).status_code == 422
    assert _create_account(client, admin_headers).status_code == 201
    assert _create_account(client, admin_headers).status_code == 409
    assert _create_account(
        client,
        admin_headers,
        institutional_email="doce@universidad.edu.co",
        identification="DOC-012",
        password="abcdefghijkl",
    ).status_code == 201
    assert _create_account(
        client,
        admin_headers,
        institutional_email="otra@universidad.edu.co",
        identification="DOC-001",
    ).status_code == 409


def test_non_admin_cannot_create_or_manage_accounts(client):
    admin_headers = _bootstrap_admin(client)
    created = _create_account(client, admin_headers)
    requester_id = created.json()["id"]
    client.patch(
        f"/users/{requester_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    requester_login = _login(client, "docente@universidad.edu.co", "una-clave-larga")
    requester_headers = {
        "Authorization": f"Bearer {requester_login.json()['access_token']}"
    }

    assert _create_account(client, requester_headers).status_code == 403
    assert client.get("/users", headers=requester_headers).status_code == 403
    assert client.patch(
        f"/users/{requester_id}/status",
        headers=requester_headers,
        json={"is_active": False},
    ).status_code == 403
    assert (
        client.patch(
            f"/users/{requester_id}/role",
            headers=requester_headers,
            json={"role": "administrator"},
        ).status_code
        == 403
    )


def test_account_activation_deactivation_blocks_session_and_preserves_reservations(
    client,
):
    admin_headers = _bootstrap_admin(client)
    created = _create_account(client, admin_headers)
    user_id = created.json()["id"]
    activation = client.patch(
        f"/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert activation.status_code == 200

    user_login = _login(client, "docente@universidad.edu.co", "una-clave-larga")
    user_token = user_login.json()["access_token"]
    with database_connection() as connection:
        connection.execute(
            """INSERT INTO spaces (
                   name, type, capacity, location, requires_approval, created_at_utc
               ) VALUES ('Sala', 'aula', 10, 'Edificio A', 0, '2098-01-01T00:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status, created_at_utc
               ) VALUES (?, 1, '2099-01-01T08:00:00+00:00',
                         '2099-01-01T09:00:00+00:00', 'approved',
                         '2098-01-01T00:00:00+00:00')""",
            (user_id,),
        )

    deactivation = client.patch(
        f"/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivation.status_code == 200
    assert deactivation.json()["future_reservations_to_review"] == 1
    assert client.get("/users", headers={"Authorization": f"Bearer {user_token}"}).status_code == 401
    assert _login(client, "docente@universidad.edu.co", "una-clave-larga").status_code == 401
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM reservations").fetchone()[0] == 1
        assert connection.execute(
            "SELECT is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()[0] == 0
        assert [
            row[0]
            for row in connection.execute(
                """SELECT action FROM history_events
                   WHERE entity_type = 'user' AND entity_id = ?
                   ORDER BY occurred_at_utc, id""",
                (user_id,),
            )
        ] == ["user_created", "user_activated", "user_deactivated"]

    reactivation = client.patch(
        f"/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert reactivation.status_code == 200
    assert _login(client, "docente@universidad.edu.co", "una-clave-larga").status_code == 200


def test_admin_role_changes_and_assigns_only_approver_accounts(client):
    admin_headers = _bootstrap_admin(client)
    approver = _create_account(
        client,
        admin_headers,
        institutional_email="aprobador@universidad.edu.co",
        identification="APR-1",
        role="approver",
    ).json()
    requester = _create_account(
        client,
        admin_headers,
        institutional_email="solicitante@universidad.edu.co",
        identification="SOL-1",
    ).json()
    with database_connection() as connection:
        connection.execute(
            """INSERT INTO spaces (
                   name, type, capacity, location, requires_approval, created_at_utc
               ) VALUES ('Auditorio', 'auditorio', 40, 'Edificio B', 1,
                         '2026-01-01T00:00:00+00:00')"""
        )

    assert client.put(
        f"/permissions/spaces/1/approvers/{approver['id']}", headers=admin_headers
    ).status_code == 204
    assert get_approver_space_ids(approver["id"]) == {1}
    assert client.put(
        f"/permissions/spaces/1/approvers/{requester['id']}", headers=admin_headers
    ).status_code == 422
    client.patch(
        f"/users/{requester['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    requester_login = _login(
        client, "solicitante@universidad.edu.co", "una-clave-larga"
    )
    requester_headers = {
        "Authorization": f"Bearer {requester_login.json()['access_token']}"
    }
    assert client.put(
        f"/permissions/spaces/{1}/approvers/{approver['id']}",
        headers=requester_headers,
    ).status_code == 403
    assert client.delete(
        f"/permissions/spaces/1/approvers/{approver['id']}", headers=admin_headers
    ).status_code == 204
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM space_approvers").fetchone()[0] == 0

    changed_role = client.patch(
        f"/users/{requester['id']}/role",
        headers=admin_headers,
        json={"role": "approver"},
    )
    assert changed_role.status_code == 200
    assert changed_role.json()["role"] == "approver"


def test_role_matrix_scopes_reservation_access_and_approval():
    requester = Principal(user_id=10, role="requester", is_active=True)
    assigned_approver = Principal(user_id=20, role="approver", is_active=True)
    inactive_admin = Principal(user_id=30, role="administrator", is_active=False)

    assert can_administer(Principal(1, "administrator", True))
    assert not can_administer(requester)
    assert can_view_reservation(
        requester,
        owner_user_id=10,
        space_id=5,
        assigned_space_ids=set(),
    )
    assert not can_change_reservation(
        requester,
        owner_user_id=11,
        space_id=5,
        assigned_space_ids=set(),
    )
    assert can_view_reservation(
        assigned_approver,
        owner_user_id=10,
        space_id=5,
        assigned_space_ids={5},
    )
    assert can_decide_reservation(
        assigned_approver,
        owner_user_id=10,
        space_id=5,
        assigned_space_ids={5},
    )
    assert not can_decide_reservation(
        assigned_approver,
        owner_user_id=20,
        space_id=5,
        assigned_space_ids={5},
    )
    assert not can_decide_reservation(
        assigned_approver,
        owner_user_id=10,
        space_id=6,
        assigned_space_ids={5},
    )
    assert not can_view_reservation(
        inactive_admin,
        owner_user_id=10,
        space_id=5,
        assigned_space_ids=set(),
    )
