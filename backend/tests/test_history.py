from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.main import app
from backend.usuarios.service import create_initial_admin


@pytest.fixture
def history_api(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ACADEMIC_RESERVATIONS_DB_PATH", str(tmp_path / "history.sqlite3")
    )
    with TestClient(app) as client:
        create_initial_admin(
            full_name="Administradora",
            institutional_email="admin@universidad.edu.co",
            password="abcdefghijkl",
        )
        admin_headers = _login(client, "admin@universidad.edu.co", "abcdefghijkl")
        requester = _create_user(client, admin_headers, "solicitante@universidad.edu.co", "requester")
        other_requester = _create_user(client, admin_headers, "otra@universidad.edu.co", "requester")
        approver = _create_user(client, admin_headers, "aprobador@universidad.edu.co", "approver")
        assigned_space = _create_space(client, admin_headers, "Sala asignada")
        other_space = _create_space(client, admin_headers, "Sala ajena")
        assert client.put(
            f"/permissions/spaces/{assigned_space['id']}/approvers/{approver['id']}",
            headers=admin_headers,
        ).status_code == 204
        yield {
            "client": client,
            "admin_headers": admin_headers,
            "requester": requester,
            "requester_headers": _login(client, "solicitante@universidad.edu.co", "una-clave-larga"),
            "other_requester": other_requester,
            "other_headers": _login(client, "otra@universidad.edu.co", "una-clave-larga"),
            "approver": approver,
            "approver_headers": _login(client, "aprobador@universidad.edu.co", "una-clave-larga"),
            "assigned_space": assigned_space,
            "other_space": other_space,
        }


def _login(client, email, password):
    response = client.post(
        "/auth/login",
        json={"institutional_email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_user(client, admin_headers, email, role):
    response = client.post(
        "/users",
        headers=admin_headers,
        json={
            "full_name": email.split("@")[0],
            "institutional_email": email,
            "identification": email.split("@")[0],
            "password": "una-clave-larga",
            "role": role,
        },
    )
    assert response.status_code == 201
    user = response.json()
    assert client.patch(
        f"/users/{user['id']}/status", headers=admin_headers,
        json={"is_active": True},
    ).status_code == 200
    return user


def _create_space(client, admin_headers, name):
    response = client.post(
        "/spaces",
        headers=admin_headers,
        json={
            "name": name,
            "type": "aula",
            "capacity": 20,
            "location": "Edificio A",
            "equipment": [],
            "is_active": True,
            "requires_approval": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def _future_interval(days=5):
    local_zone = ZoneInfo("America/Bogota")
    day = datetime.now(local_zone).date() + timedelta(days=days)
    while day.weekday() == 6:
        day += timedelta(days=1)
    start = datetime(day.year, day.month, day.day, 8, tzinfo=local_zone)
    return start, start + timedelta(hours=1)


def _create_pending(client, headers, space_id):
    start, end = _future_interval()
    response = client.post(
        "/reservations",
        headers=headers,
        json={"space_id": space_id, "starts_at": start.isoformat(), "ends_at": end.isoformat()},
    )
    assert response.status_code == 201
    return response.json()


def test_account_role_and_assignment_events_keep_actor_and_values(history_api):
    api = history_api
    user_id = api["requester"]["id"]
    changed_role = api["client"].patch(
        f"/users/{user_id}/role", headers=api["admin_headers"],
        json={"role": "approver"},
    )
    assert changed_role.status_code == 200
    assert api["client"].put(
        f"/permissions/spaces/{api['other_space']['id']}/approvers/{user_id}",
        headers=api["admin_headers"],
    ).status_code == 204
    assert api["client"].delete(
        f"/permissions/spaces/{api['other_space']['id']}/approvers/{user_id}",
        headers=api["admin_headers"],
    ).status_code == 204

    user_events = api["client"].get(
        f"/history?entity_type=user&entity_id={user_id}",
        headers=api["admin_headers"],
    )
    assert user_events.status_code == 200
    events = user_events.json()
    assert [event["action"] for event in events] == [
        "user_created", "user_activated", "user_role_changed"
    ]
    assert all(event["actor_user_id"] == 1 for event in events)
    assert events[-1]["old_values"] == {"role": "requester"}
    assert events[-1]["new_values"] == {"role": "approver"}
    assert "password" not in str(events)

    space_events = api["client"].get(
        f"/history?entity_type=space&entity_id={api['other_space']['id']}",
        headers=api["admin_headers"],
    ).json()
    assert [event["action"] for event in space_events] == [
        "space_created", "space_approver_assigned", "space_approver_removed"
    ]
    assert space_events[1]["new_values"] == {"approver_user_id": user_id}


def test_history_scope_reason_order_and_account_deactivation_retention(history_api):
    api = history_api
    owned = _create_pending(
        api["client"], api["requester_headers"], api["assigned_space"]["id"]
    )
    other = _create_pending(
        api["client"], api["other_headers"], api["other_space"]["id"]
    )
    rejected = api["client"].post(
        f"/approvals/reservations/{owned['id']}/decision",
        headers=api["approver_headers"],
        json={"decision": "reject", "reason": "Falta de justificación"},
    )
    assert rejected.status_code == 200

    own_history = api["client"].get("/history", headers=api["requester_headers"])
    assert own_history.status_code == 200
    assert {event["entity_id"] for event in own_history.json()} == {owned["id"]}
    assert [event["action"] for event in own_history.json()] == [
        "reservation_created", "reservation_rejected"
    ]
    assert own_history.json()[-1]["reason"] == "Falta de justificación"
    assert own_history.json()[0]["occurred_at_utc"] <= own_history.json()[1]["occurred_at_utc"]

    approver_history = api["client"].get("/history", headers=api["approver_headers"])
    assert approver_history.status_code == 200
    assert {event["entity_id"] for event in approver_history.json()} == {owned["id"]}
    assert api["client"].get(
        f"/history?entity_type=reservation&entity_id={other['id']}",
        headers=api["requester_headers"],
    ).status_code == 404

    assert api["client"].patch(
        f"/users/{api['requester']['id']}/status", headers=api["admin_headers"],
        json={"is_active": False},
    ).status_code == 200
    retained = api["client"].get(
        f"/history?entity_type=user&entity_id={api['requester']['id']}",
        headers=api["admin_headers"],
    )
    assert retained.status_code == 200
    assert [event["action"] for event in retained.json()] == [
        "user_created", "user_activated", "user_deactivated"
    ]


def test_history_is_read_only_and_requires_authentication(history_api):
    api = history_api
    before = len(api["client"].get("/history", headers=api["admin_headers"]).json())
    assert api["client"].get("/history").status_code == 401
    assert api["client"].delete("/history", headers=api["admin_headers"]).status_code == 405
    assert api["client"].patch("/history", headers=api["admin_headers"], json={}).status_code == 405
    after = len(api["client"].get("/history", headers=api["admin_headers"]).json())
    assert before == after


def test_approver_can_read_assigned_space_history_after_block_deletion(history_api):
    api = history_api
    starts_at, ends_at = _future_interval(days=9)
    created = api["client"].post(
        f"/spaces/{api['assigned_space']['id']}/maintenance-blocks",
        headers=api["admin_headers"],
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "reason": "Inspección",
        },
    )
    assert created.status_code == 201
    block_id = created.json()["id"]
    assert api["client"].delete(
        f"/spaces/{api['assigned_space']['id']}/maintenance-blocks/{block_id}",
        headers=api["admin_headers"],
    ).status_code == 204

    history = api["client"].get(
        f"/history?entity_type=maintenance_block&entity_id={block_id}",
        headers=api["approver_headers"],
    )
    assert history.status_code == 200
    assert [event["action"] for event in history.json()] == [
        "maintenance_block_created", "maintenance_block_deleted"
    ]

