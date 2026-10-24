from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.main import app
from backend.politicas.validation import LOCAL_TIMEZONE
from backend.reservas.service import (
    CancellationReasonRequiredError,
    ReservationConflictError,
    ReservationForbiddenError,
    ReservationNotFoundError,
    cancel_reservation,
    create_reservation,
    list_reservations,
)
from backend.usuarios.permissions import Principal
from backend.usuarios.service import create_initial_admin


@pytest.fixture
def reservation_api(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ACADEMIC_RESERVATIONS_DB_PATH", str(tmp_path / "reservations.sqlite3")
    )
    with TestClient(app) as client:
        create_initial_admin(
            full_name="Administradora",
            institutional_email="admin@universidad.edu.co",
            password="abcdefghijkl",
        )
        admin_headers = _login(client, "admin@universidad.edu.co")
        requester = _create_user(
            client, admin_headers, "solicitante@universidad.edu.co", "requester"
        )
        other_requester = _create_user(
            client, admin_headers, "otra@universidad.edu.co", "requester"
        )
        approver = _create_user(
            client, admin_headers, "aprobador@universidad.edu.co", "approver"
        )
        space = _create_space(client, admin_headers, requires_approval=True)
        other_space = _create_space(
            client,
            admin_headers,
            name="Sala alterna",
            requires_approval=False,
        )
        assert client.put(
            f"/permissions/spaces/{space['id']}/approvers/{approver['id']}",
            headers=admin_headers,
        ).status_code == 204
        yield {
            "client": client,
            "admin_headers": admin_headers,
            "requester": requester,
            "requester_headers": _login(
                client, "solicitante@universidad.edu.co"
            ),
            "other_requester": other_requester,
            "other_requester_headers": _login(client, "otra@universidad.edu.co"),
            "approver": approver,
            "approver_headers": _login(client, "aprobador@universidad.edu.co"),
            "space": space,
            "other_space": other_space,
        }


def _login(client, email):
    password = (
        "abcdefghijkl"
        if email == "admin@universidad.edu.co"
        else "una-clave-larga"
    )
    response = client.post(
        "/auth/login",
        json={"institutional_email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_user(client, admin_headers, email, role):
    user = client.post(
        "/users",
        headers=admin_headers,
        json={
            "full_name": role.title(),
            "institutional_email": email,
            "identification": email.split("@")[0],
            "password": "una-clave-larga",
            "role": role,
        },
    )
    assert user.status_code == 201
    account = user.json()
    activated = client.patch(
        f"/users/{account['id']}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert activated.status_code == 200
    return account


def _create_space(client, admin_headers, *, name="Laboratorio", requires_approval):
    response = client.post(
        "/spaces",
        headers=admin_headers,
        json={
            "name": name,
            "type": "laboratorio",
            "capacity": 20,
            "location": "Edificio A",
            "equipment": [],
            "is_active": True,
            "requires_approval": requires_approval,
        },
    )
    assert response.status_code == 201
    return response.json()


def _insert_reservation(
    *, user_id, space_id, status, starts_at, ends_at, cancellation_reason=None
):
    with database_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO reservations (
                   user_id, space_id, starts_at_utc, ends_at_utc, status,
                   created_at_utc, cancellation_reason
               ) VALUES (?, ?, ?, ?, ?, '2029-01-01T00:00:00+00:00', ?)""",
            (
                user_id,
                space_id,
                starts_at.isoformat(),
                ends_at.isoformat(),
                status,
                cancellation_reason,
            ),
        )
        return cursor.lastrowid


def _future_interval(days=7):
    local_date = datetime.now(LOCAL_TIMEZONE).date() + timedelta(days=days)
    while local_date.weekday() == 6:
        local_date += timedelta(days=1)
    starts_at = datetime(
        local_date.year, local_date.month, local_date.day, 8, 0,
        tzinfo=LOCAL_TIMEZONE,
    )
    ends_at = starts_at + timedelta(hours=1)
    requested_at = starts_at.astimezone(timezone.utc) - timedelta(hours=24)
    return starts_at, ends_at, requested_at


def test_service_persists_and_queries_initial_state_from_space_policy(reservation_api):
    requester_id = reservation_api["requester"]["id"]
    other_requester_id = reservation_api["other_requester"]["id"]
    starts_at, ends_at, request_time = _future_interval()

    pending = create_reservation(
        user_id=requester_id,
        space_id=reservation_api["space"]["id"],
        starts_at=starts_at,
        ends_at=ends_at,
        created_at=request_time,
    )
    approved = create_reservation(
        user_id=other_requester_id,
        space_id=reservation_api["other_space"]["id"],
        starts_at=starts_at,
        ends_at=ends_at,
        created_at=request_time,
    )

    assert pending["status"] == "pending"
    assert approved["status"] == "approved"
    assert pending["starts_at_utc"] == starts_at.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    )
    own_rows = list_reservations(
        principal=Principal(
            user_id=requester_id, role="requester", is_active=True
        ),
        now=request_time,
    )
    assert [row["id"] for row in own_rows] == [pending["id"]]


def test_reservation_queries_are_limited_by_role_and_space(reservation_api):
    starts_at, ends_at, _ = _future_interval(days=12)
    pending = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="pending",
        starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    approved = _insert_reservation(
        user_id=reservation_api["other_requester"]["id"],
        space_id=reservation_api["other_space"]["id"],
        status="approved",
        starts_at=(starts_at + timedelta(hours=2)).astimezone(timezone.utc),
        ends_at=(ends_at + timedelta(hours=2)).astimezone(timezone.utc),
    )
    client = reservation_api["client"]

    admin_rows = client.get(
        "/reservations", headers=reservation_api["admin_headers"]
    ).json()
    approver_rows = client.get(
        "/reservations", headers=reservation_api["approver_headers"]
    ).json()
    assert [row["id"] for row in admin_rows] == [pending, approved]
    assert [row["id"] for row in approver_rows] == [pending]
    assert client.get(
        f"/reservations/{approved}", headers=reservation_api["requester_headers"]
    ).status_code == 404
    assert client.get(
        f"/reservations/{pending}", headers=reservation_api["requester_headers"]
    ).json()["space_name"] == "Laboratorio"


def test_query_finalizes_expired_approved_reservation(reservation_api):
    now = datetime(2030, 1, 3, 12, tzinfo=timezone.utc)
    user_id = reservation_api["requester"]["id"]
    space_id = reservation_api["space"]["id"]
    approved_id = _insert_reservation(
        user_id=user_id,
        space_id=space_id,
        status="approved",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )
    visible = list_reservations(
        principal=Principal(user_id=user_id, role="requester", is_active=True),
        now=now,
    )

    states = {row["id"]: row["status"] for row in visible}
    assert states[approved_id] == "finished"


def test_requester_cancels_pending_reservation_and_keeps_optional_reason(reservation_api):
    user_id = reservation_api["requester"]["id"]
    reservation_id = _insert_reservation(
        user_id=user_id,
        space_id=reservation_api["space"]["id"],
        status="pending",
        starts_at=datetime(2030, 1, 2, 12, tzinfo=timezone.utc),
        ends_at=datetime(2030, 1, 2, 13, tzinfo=timezone.utc),
    )

    response = reservation_api["client"].post(
        f"/reservations/{reservation_id}/cancel",
        headers=reservation_api["requester_headers"],
        json={"reason": "  Cambio de actividad  "},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancellation_reason"] == "Cambio de actividad"


def test_requester_cancels_approved_reservation_at_two_hour_boundary(reservation_api):
    now = datetime(2030, 1, 1, 8, tzinfo=timezone.utc)
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="approved",
        starts_at=now + timedelta(hours=2),
        ends_at=now + timedelta(hours=3),
    )

    result = cancel_reservation(
        reservation_id=reservation_id,
        actor_user_id=reservation_api["requester"]["id"],
        actor_role="requester",
        now=now,
    )

    assert result["status"] == "cancelled"
    assert result["cancellation_reason"] is None


def test_requester_cannot_cancel_approved_reservation_inside_two_hour_cutoff(
    reservation_api,
):
    now = datetime(2030, 1, 1, 8, tzinfo=timezone.utc)
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="approved",
        starts_at=now + timedelta(hours=1, minutes=59, seconds=59),
        ends_at=now + timedelta(hours=3),
    )

    with pytest.raises(ReservationConflictError, match="dos horas"):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=reservation_api["requester"]["id"],
            actor_role="requester",
            now=now,
        )
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"] == "approved"
    assert reservation_api["client"].get(
        f"/reservations/{reservation_id}", headers=reservation_api["requester_headers"]
    ).json()["status"] == "approved"


@pytest.mark.parametrize("reservation_status", ["pending", "approved"])
def test_administrator_must_give_reason_and_can_cancel_with_reason(
    reservation_api, reservation_status
):
    now = datetime.now(timezone.utc)
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status=reservation_status,
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=3, hours=1),
    )

    with pytest.raises(CancellationReasonRequiredError):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=1,
            actor_role="administrator",
            now=now,
        )
    missing_reason = reservation_api["client"].post(
        f"/reservations/{reservation_id}/cancel",
        headers=reservation_api["admin_headers"],
    )
    assert missing_reason.status_code == 422
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"] == reservation_status
    response = reservation_api["client"].post(
        f"/reservations/{reservation_id}/cancel",
        headers=reservation_api["admin_headers"],
        json={"reason": "Cierre institucional"},
    )
    assert response.status_code == 200
    assert response.json()["cancellation_reason"] == "Cierre institucional"
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, new_values_json FROM history_events
               WHERE entity_type = 'reservation' AND entity_id = ?""",
            (reservation_id,),
        ).fetchone()
    assert event["action"] == "reservation_cancelled"
    assert '"cancellation_reason": "Cierre institucional"' in event["new_values_json"]


def test_cancel_attempt_finalizes_an_expired_approved_reservation(reservation_api):
    now = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="approved",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )

    with pytest.raises(ReservationConflictError, match="finalizada"):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=reservation_api["requester"]["id"],
            actor_role="requester",
            now=now,
        )
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"] == "finished"


def test_requester_cannot_cancel_another_users_reservation(reservation_api):
    reservation_id = _insert_reservation(
        user_id=reservation_api["other_requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="pending",
        starts_at=datetime(2030, 1, 2, 12, tzinfo=timezone.utc),
        ends_at=datetime(2030, 1, 2, 13, tzinfo=timezone.utc),
    )

    with pytest.raises(ReservationNotFoundError):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=reservation_api["requester"]["id"],
            actor_role="requester",
        )
    assert reservation_api["client"].get(
        f"/reservations/{reservation_id}", headers=reservation_api["admin_headers"]
    ).json()["status"] == "pending"


def test_approver_cannot_cancel_reservations(reservation_api):
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status="pending",
        starts_at=datetime(2030, 1, 2, 12, tzinfo=timezone.utc),
        ends_at=datetime(2030, 1, 2, 13, tzinfo=timezone.utc),
    )

    with pytest.raises(ReservationForbiddenError):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=reservation_api["approver"]["id"],
            actor_role="approver",
        )


@pytest.mark.parametrize("terminal_status", ["rejected", "cancelled", "finished"])
def test_terminal_reservations_cannot_be_cancelled_or_reopened(
    reservation_api, terminal_status
):
    reservation_id = _insert_reservation(
        user_id=reservation_api["requester"]["id"],
        space_id=reservation_api["space"]["id"],
        status=terminal_status,
        starts_at=datetime(2030, 1, 2, 12, tzinfo=timezone.utc),
        ends_at=datetime(2030, 1, 2, 13, tzinfo=timezone.utc),
    )

    with pytest.raises(ReservationConflictError):
        cancel_reservation(
            reservation_id=reservation_id,
            actor_user_id=reservation_api["requester"]["id"],
            actor_role="requester",
        )
    assert reservation_api["client"].get(
        f"/reservations/{reservation_id}", headers=reservation_api["admin_headers"]
    ).json()["status"] == terminal_status
