"""End-to-end API journey across the approved reservation capabilities."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from backend.main import app
from backend.usuarios.service import create_initial_admin


def _login(client, email, password):
    response = client.post(
        "/auth/login",
        json={"institutional_email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _booking_interval():
    zone = ZoneInfo("America/Bogota")
    day = datetime.now(zone).date() + timedelta(days=5)
    while day.weekday() == 6:
        day += timedelta(days=1)
    start = datetime(day.year, day.month, day.day, 8, 0, tzinfo=zone)
    return start, start + timedelta(hours=1)


def test_complete_account_space_reservation_approval_cancellation_history_journey(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "ACADEMIC_RESERVATIONS_DB_PATH", str(tmp_path / "integration.sqlite3")
    )
    with TestClient(app) as client:
        create_initial_admin(
            full_name="Administradora",
            institutional_email="admin@universidad.edu.co",
            password="abcdefghijkl",
        )
        admin_headers = _login(
            client, "admin@universidad.edu.co", "abcdefghijkl"
        )

        created_user = client.post(
            "/users",
            headers=admin_headers,
            json={
                "full_name": "Solicitante de integración",
                "institutional_email": "integracion@universidad.edu.co",
                "identification": "INTEGRACION-01",
                "password": "clave-integracion",
                "role": "requester",
            },
        )
        assert created_user.status_code == 201
        requester = created_user.json()
        assert requester["is_active"] is False
        assert client.post(
            "/auth/login",
            json={
                "institutional_email": "integracion@universidad.edu.co",
                "password": "clave-integracion",
            },
        ).status_code == 401
        assert client.patch(
            f"/users/{requester['id']}/status",
            headers=admin_headers,
            json={"is_active": True},
        ).status_code == 200
        requester_headers = _login(
            client, "integracion@universidad.edu.co", "clave-integracion"
        )

        approver_response = client.post(
            "/users",
            headers=admin_headers,
            json={
                "full_name": "Aprobador de integración",
                "institutional_email": "aprobador.integracion@universidad.edu.co",
                "identification": "INTEGRACION-02",
                "password": "clave-integracion",
                "role": "approver",
            },
        )
        assert approver_response.status_code == 201
        approver = approver_response.json()
        assert client.patch(
            f"/users/{approver['id']}/status",
            headers=admin_headers,
            json={"is_active": True},
        ).status_code == 200
        approver_headers = _login(
            client,
            "aprobador.integracion@universidad.edu.co",
            "clave-integracion",
        )

        created_space = client.post(
            "/spaces",
            headers=admin_headers,
            json={
                "name": "Aula de integración",
                "type": "aula",
                "capacity": 24,
                "location": "Edificio de pruebas",
                "equipment": ["Proyector"],
                "is_active": True,
                "requires_approval": True,
            },
        )
        assert created_space.status_code == 201
        space_id = created_space.json()["id"]
        assert client.put(
            f"/permissions/spaces/{space_id}/approvers/{approver['id']}",
            headers=admin_headers,
        ).status_code == 204

        starts_at, ends_at = _booking_interval()
        params = {
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        }
        available = client.get(
            f"/availability/spaces/{space_id}",
            headers=requester_headers,
            params=params,
        )
        assert available.status_code == 200
        assert available.json()["availability"] == "available"

        first_request = client.post(
            "/reservations",
            headers=requester_headers,
            json={"space_id": space_id, **params},
        )
        assert first_request.status_code == 201
        first_reservation_id = first_request.json()["id"]
        assert first_request.json()["status"] == "pending"
        assert client.get(
            f"/availability/spaces/{space_id}",
            headers=requester_headers,
            params=params,
        ).json()["availability"] == "occupied"

        pending = client.get("/approvals/pending", headers=approver_headers)
        assert pending.status_code == 200
        assert [item["id"] for item in pending.json()] == [first_reservation_id]
        rejected = client.post(
            f"/approvals/reservations/{first_reservation_id}/decision",
            headers=approver_headers,
            json={"decision": "reject", "reason": "Falta de justificación"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"
        assert client.get(
            f"/availability/spaces/{space_id}",
            headers=requester_headers,
            params=params,
        ).json()["availability"] == "available"

        second_request = client.post(
            "/reservations",
            headers=requester_headers,
            json={"space_id": space_id, **params},
        )
        assert second_request.status_code == 201
        second_reservation_id = second_request.json()["id"]
        approved = client.post(
            f"/approvals/reservations/{second_reservation_id}/decision",
            headers=approver_headers,
            json={"decision": "approve"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        cancelled = client.post(
            f"/reservations/{second_reservation_id}/cancel",
            headers=requester_headers,
            json={"reason": "Cambio de agenda"},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["cancellation_reason"] == "Cambio de agenda"
        assert client.get(
            f"/availability/spaces/{space_id}",
            headers=requester_headers,
            params=params,
        ).json()["availability"] == "available"

        history = client.get(
            f"/history?entity_type=reservation&entity_id={first_reservation_id}",
            headers=admin_headers,
        )
        assert history.status_code == 200
        assert [event["action"] for event in history.json()] == [
            "reservation_created", "reservation_rejected"
        ]
        assert history.json()[-1]["reason"] == "Falta de justificación"
        cancellation_history = client.get(
            f"/history?entity_type=reservation&entity_id={second_reservation_id}",
            headers=admin_headers,
        )
        assert [event["action"] for event in cancellation_history.json()] == [
            "reservation_created", "reservation_approved", "reservation_cancelled"
        ]
        assert cancellation_history.json()[-1]["reason"] == "Cambio de agenda"

