from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import time

import pytest
from fastapi.testclient import TestClient

from backend.database import database_connection
from backend.disponibilidad.service import query_availability
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
    update_reservation,
)
from backend.reservas.states import expire_due_pending_reservations
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


def test_api_creates_reservations_with_initial_status_and_rejects_invalid_requests(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval()
    client = api["client"]
    pending = client.post(
        "/reservations", headers=api["requester_headers"],
        json={"space_id": api["space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )
    approved = client.post(
        "/reservations", headers=api["requester_headers"],
        json={"space_id": api["other_space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )
    assert pending.status_code == 201 and pending.json()["status"] == "pending"
    assert approved.status_code == 201 and approved.json()["status"] == "approved"

    conflict = client.post(
        "/reservations", headers=api["requester_headers"],
        json={"space_id": api["other_space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )
    assert conflict.status_code == 409
    invalid_start = starts_at.replace(hour=6)
    invalid_end = starts_at.replace(hour=7)
    invalid = client.post(
        "/reservations", headers=api["requester_headers"],
        json={"space_id": api["other_space"]["id"], "starts_at": invalid_start.isoformat(), "ends_at": invalid_end.isoformat()},
    )
    assert invalid.status_code == 422
    assert client.post(
        "/reservations", headers=api["approver_headers"],
        json={"space_id": api["other_space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    ).status_code == 403
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) AS total FROM reservations").fetchone()["total"] == 2


def test_api_rejects_inactive_space_and_deactivated_requester(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval()
    client = api["client"]
    inactive_space = _create_space(client, api["admin_headers"], name="Inactiva", requires_approval=False)
    assert client.patch(
        f"/spaces/{inactive_space['id']}/status", headers=api["admin_headers"], json={"is_active": False}
    ).status_code == 200
    payload = {"space_id": inactive_space["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()}
    assert client.post("/reservations", headers=api["requester_headers"], json=payload).status_code == 409

    assert client.patch(
        f"/users/{api['requester']['id']}/status", headers=api["admin_headers"], json={"is_active": False}
    ).status_code == 200
    assert client.post("/reservations", headers=api["requester_headers"], json=payload).status_code == 401
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) AS total FROM reservations").fetchone()["total"] == 0


def test_api_rejects_maintenance_conflicts_without_creating_reservation(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=11)
    block = api["client"].post(
        f"/spaces/{api['space']['id']}/maintenance-blocks",
        headers=api["admin_headers"],
        json={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat(), "reason": "Mantenimiento"},
    )
    assert block.status_code == 201
    response = api["client"].post(
        "/reservations", headers=api["requester_headers"],
        json={"space_id": api["space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )
    assert response.status_code == 409
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) AS total FROM reservations").fetchone()["total"] == 0


def test_simultaneous_incompatible_requests_accept_at_most_one(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval()
    payload = {"space_id": api["space"]["id"], "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()}

    def submit(_):
        return api["client"].post("/reservations", headers=api["requester_headers"], json=payload).status_code

    with ThreadPoolExecutor(max_workers=20) as workers:
        statuses = list(workers.map(submit, range(20)))
    assert statuses.count(201) == 1
    assert all(code in {201, 409, 503} for code in statuses)
    with database_connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS total FROM reservations WHERE space_id = ? AND status IN ('pending', 'approved')",
            (api["space"]["id"],),
        ).fetchone()["total"] == 1


def test_pending_reservation_modification_checks_owner_policies_and_availability(reservation_api):
    api = reservation_api
    starts_at, ends_at, requested_at = _future_interval(days=9)
    reservation = create_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        starts_at=starts_at, ends_at=ends_at, created_at=requested_at,
    )
    client = api["client"]
    new_start = starts_at + timedelta(hours=2)
    new_end = ends_at + timedelta(hours=2)
    payload = {"starts_at": new_start.isoformat(), "ends_at": new_end.isoformat()}

    forbidden = client.put(
        f"/reservations/{reservation['id']}", headers=api["other_requester_headers"], json=payload
    )
    assert forbidden.status_code == 404
    changed = client.put(
        f"/reservations/{reservation['id']}", headers=api["requester_headers"], json=payload
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "pending"
    assert changed.json()["starts_at_utc"] == new_start.astimezone(timezone.utc).isoformat(timespec="microseconds")

    bad_start = new_start.replace(hour=6)
    bad_end = new_end.replace(hour=7)
    invalid = client.put(
        f"/reservations/{reservation['id']}", headers=api["requester_headers"],
        json={"starts_at": bad_start.isoformat(), "ends_at": bad_end.isoformat()},
    )
    assert invalid.status_code == 422
    current = client.get(f"/reservations/{reservation['id']}", headers=api["requester_headers"]).json()
    assert current["starts_at_utc"] == changed.json()["starts_at_utc"]


def test_approved_modification_requests_approval_when_space_requires_it(reservation_api):
    api = reservation_api
    begins_local, ends_local, _ = _future_interval(days=10)
    begins = begins_local.astimezone(timezone.utc)
    ends = ends_local.astimezone(timezone.utc)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=begins, ends_at=ends,
    )
    next_start = begins + timedelta(hours=2)
    response = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": next_start.isoformat(), "ends_at": (next_start + timedelta(hours=1)).isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["pending_change"] is not None
    with database_connection() as connection:
        stored = connection.execute(
            "SELECT starts_at_utc, status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
        assert stored["starts_at_utc"] == begins.isoformat()
        assert stored["status"] == "approved"

    other_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["other_space"]["id"],
        status="approved", starts_at=begins, ends_at=ends,
    )
    changed = api["client"].put(
        f"/reservations/{other_id}", headers=api["requester_headers"],
        json={"starts_at": next_start.isoformat(), "ends_at": (next_start + timedelta(hours=1)).isoformat()},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "approved"


def test_approved_modification_respects_two_hour_deadline(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    starts_at = now + timedelta(hours=1, minutes=59)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["other_space"]["id"],
        status="approved", starts_at=starts_at, ends_at=starts_at + timedelta(hours=1),
    )
    target_start, target_end, _ = _future_interval(days=14)
    with pytest.raises(ReservationConflictError, match="dos horas"):
        update_reservation(
            reservation_id=reservation_id,
            actor_user_id=api["requester"]["id"],
            starts_at=target_start,
            ends_at=target_end,
            now=now,
        )
    with database_connection() as connection:
        stored = connection.execute(
            "SELECT starts_at_utc, status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
    assert stored["starts_at_utc"] == starts_at.isoformat()
    assert stored["status"] == "approved"


def test_approved_modification_is_allowed_at_two_hour_boundary(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    starts_at = now + timedelta(hours=2)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["other_space"]["id"],
        status="approved", starts_at=starts_at, ends_at=starts_at + timedelta(hours=1),
    )
    target_start, target_end, _ = _future_interval(days=15)
    changed = update_reservation(
        reservation_id=reservation_id,
        actor_user_id=api["requester"]["id"],
        starts_at=target_start,
        ends_at=target_end,
        now=now,
    )
    assert changed["status"] == "approved"
    assert changed["starts_at_utc"] == target_start.astimezone(timezone.utc).isoformat(timespec="microseconds")


@pytest.mark.parametrize("occupied_status", ["pending", "approved"])
def test_pending_modification_rejects_new_interval_occupied_by_active_reservation(
    reservation_api, occupied_status
):
    api = reservation_api
    original_start, original_end, requested_at = _future_interval(days=12)
    reservation = create_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        starts_at=original_start, ends_at=original_end, created_at=requested_at,
    )
    occupied_start, occupied_end, _ = _future_interval(days=13)
    _insert_reservation(
        user_id=api["other_requester"]["id"], space_id=api["space"]["id"],
        status=occupied_status,
        starts_at=occupied_start.astimezone(timezone.utc),
        ends_at=occupied_end.astimezone(timezone.utc),
    )
    response = api["client"].put(
        f"/reservations/{reservation['id']}", headers=api["requester_headers"],
        json={"starts_at": occupied_start.isoformat(), "ends_at": occupied_end.isoformat()},
    )
    assert response.status_code == 409
    with database_connection() as connection:
        stored = connection.execute(
            "SELECT starts_at_utc, ends_at_utc, status FROM reservations WHERE id = ?",
            (reservation["id"],),
        ).fetchone()
    assert stored["starts_at_utc"] == original_start.astimezone(timezone.utc).isoformat(timespec="microseconds")
    assert stored["ends_at_utc"] == original_end.astimezone(timezone.utc).isoformat(timespec="microseconds")
    assert stored["status"] == "pending"


@pytest.mark.parametrize("terminal_status", ["rejected", "cancelled", "finished"])
def test_terminal_reservations_cannot_be_modified(reservation_api, terminal_status):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=16)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["other_space"]["id"],
        status=terminal_status,
        starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    new_start, new_end, _ = _future_interval(days=17)
    response = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": new_start.isoformat(), "ends_at": new_end.isoformat()},
    )
    assert response.status_code == 409
    with database_connection() as connection:
        stored = connection.execute(
            "SELECT starts_at_utc, status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
    assert stored["starts_at_utc"] == starts_at.astimezone(timezone.utc).isoformat()
    assert stored["status"] == terminal_status


def test_approver_queue_only_returns_pending_reservations_for_assigned_spaces(
    reservation_api,
):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=19)
    assigned_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    unassigned_id = _insert_reservation(
        user_id=api["other_requester"]["id"], space_id=api["other_space"]["id"],
        status="pending", starts_at=(starts_at + timedelta(hours=2)).astimezone(timezone.utc),
        ends_at=(ends_at + timedelta(hours=2)).astimezone(timezone.utc),
    )

    queue = api["client"].get("/approvals/pending", headers=api["approver_headers"])
    assert queue.status_code == 200
    assert [row["id"] for row in queue.json()] == [assigned_id]
    assert unassigned_id not in {row["id"] for row in queue.json()}
    assert api["client"].get("/approvals/pending", headers=api["requester_headers"]).status_code == 403
    assert api["client"].get("/approvals/pending", headers=api["admin_headers"]).status_code == 403


def test_approver_can_approve_or_reject_assigned_pending_requests(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=20)
    approved_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    rejected_id = _insert_reservation(
        user_id=api["other_requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=(starts_at + timedelta(hours=2)).astimezone(timezone.utc),
        ends_at=(ends_at + timedelta(hours=2)).astimezone(timezone.utc),
    )
    client = api["client"]

    approved = client.post(
        f"/approvals/reservations/{approved_id}/decision",
        headers=api["approver_headers"], json={"decision": "approve"},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "approved"

    missing_reason = client.post(
        f"/approvals/reservations/{rejected_id}/decision",
        headers=api["approver_headers"], json={"decision": "reject", "reason": "  "},
    )
    assert missing_reason.status_code == 422
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (rejected_id,)
        ).fetchone()["status"] == "pending"

    rejected = client.post(
        f"/approvals/reservations/{rejected_id}/decision",
        headers=api["approver_headers"], json={"decision": "reject", "reason": "  No cumple el propósito  "},
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    with database_connection() as connection:
        event = connection.execute(
            """SELECT action, reason FROM history_events
               WHERE entity_type = 'reservation' AND entity_id = ?
               ORDER BY id DESC LIMIT 1""",
            (rejected_id,),
        ).fetchone()
    assert event["action"] == "reservation_rejected"
    assert event["reason"] == "No cumple el propósito"


def test_approver_cannot_decide_own_or_unassigned_request(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=21)
    own_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    unassigned_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["other_space"]["id"],
        status="pending", starts_at=(starts_at + timedelta(hours=2)).astimezone(timezone.utc),
        ends_at=(ends_at + timedelta(hours=2)).astimezone(timezone.utc),
    )
    changed_role = api["client"].patch(
        f"/users/{api['requester']['id']}/role", headers=api["admin_headers"],
        json={"role": "approver"},
    )
    assert changed_role.status_code == 200
    own_approver_headers = _login(api["client"], "solicitante@universidad.edu.co")
    assert api["client"].put(
        f"/permissions/spaces/{api['space']['id']}/approvers/{api['requester']['id']}",
        headers=api["admin_headers"],
    ).status_code == 204

    for reservation_id, headers in (
        (own_id, own_approver_headers),
        (unassigned_id, api["approver_headers"]),
    ):
        response = api["client"].post(
            f"/approvals/reservations/{reservation_id}/decision",
            headers=headers, json={"decision": "approve"},
        )
        assert response.status_code == 403
    with database_connection() as connection:
        statuses = connection.execute(
            "SELECT id, status FROM reservations WHERE id IN (?, ?)",
            (own_id, unassigned_id),
        ).fetchall()
    assert {row["id"]: row["status"] for row in statuses} == {
        own_id: "pending", unassigned_id: "pending"
    }


def test_concurrent_approval_decisions_apply_exactly_once(reservation_api):
    api = reservation_api
    starts_at, ends_at, _ = _future_interval(days=22)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=starts_at.astimezone(timezone.utc),
        ends_at=ends_at.astimezone(timezone.utc),
    )
    second_approver = _create_user(
        api["client"], api["admin_headers"], "aprobador2@universidad.edu.co", "approver"
    )
    assert api["client"].put(
        f"/permissions/spaces/{api['space']['id']}/approvers/{second_approver['id']}",
        headers=api["admin_headers"],
    ).status_code == 204
    second_headers = _login(api["client"], "aprobador2@universidad.edu.co")
    url = f"/approvals/reservations/{reservation_id}/decision"

    def decide(headers):
        return api["client"].post(url, headers=headers, json={"decision": "approve"}).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        statuses = list(workers.map(decide, [api["approver_headers"], second_headers]))
    assert sorted(statuses) == [200, 409]
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"] == "approved"
        assert connection.execute(
            """SELECT COUNT(*) AS total FROM history_events
               WHERE entity_type = 'reservation' AND entity_id = ?
                 AND action IN ('reservation_approved', 'reservation_rejected')""",
            (reservation_id,),
        ).fetchone()["total"] == 1


def test_pending_request_expires_with_reason_and_releases_interval(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(microsecond=0)
    starts_at = now - timedelta(minutes=1)
    ends_at = now + timedelta(minutes=30)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=starts_at, ends_at=ends_at,
    )

    assert expire_due_pending_reservations(now=now) == 1
    assert expire_due_pending_reservations(now=now) == 0
    with database_connection() as connection:
        reservation = connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
        event = connection.execute(
            """SELECT actor_user_id, action, reason, new_values_json
               FROM history_events WHERE entity_type = 'reservation' AND entity_id = ?""",
            (reservation_id,),
        ).fetchone()
    assert reservation["status"] == "rejected_expired"
    assert event["actor_user_id"] is None
    assert event["action"] == "reservation_expired"
    assert event["reason"]
    assert '"status": "rejected_expired"' in event["new_values_json"]

    availability = query_availability(
        space_id=api["space"]["id"], starts_at=starts_at, ends_at=ends_at, now=now
    )
    assert availability["availability"] == "available"


def test_approval_attempt_after_start_expires_and_rejects_decision(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(microsecond=0)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=now - timedelta(seconds=1),
        ends_at=now + timedelta(minutes=30),
    )

    response = api["client"].post(
        f"/approvals/reservations/{reservation_id}/decision",
        headers=api["approver_headers"], json={"decision": "approve"},
    )
    assert response.status_code == 409
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"] == "rejected_expired"


def test_automatic_expiration_runs_during_application_lifespan(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(microsecond=0)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=now - timedelta(seconds=1),
        ends_at=now + timedelta(minutes=30),
    )

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        with database_connection() as connection:
            state = connection.execute(
                "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()["status"]
        if state == "rejected_expired":
            break
        time.sleep(0.05)
    assert state == "rejected_expired"


def test_expiration_and_approval_race_registers_only_one_outcome(reservation_api):
    api = reservation_api
    now = datetime.now(timezone.utc).replace(microsecond=0)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="pending", starts_at=now - timedelta(seconds=1),
        ends_at=now + timedelta(minutes=30),
    )

    def approve():
        return api["client"].post(
            f"/approvals/reservations/{reservation_id}/decision",
            headers=api["approver_headers"], json={"decision": "approve"},
        ).status_code

    def expire():
        return expire_due_pending_reservations(now=now)

    with ThreadPoolExecutor(max_workers=2) as workers:
        approval_result, expiration_result = list(workers.map(lambda fn: fn(), [approve, expire]))
    assert approval_result == 409
    assert expiration_result in {0, 1}
    with database_connection() as connection:
        state = connection.execute(
            "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()["status"]
        events = connection.execute(
            """SELECT COUNT(*) AS total FROM history_events
               WHERE entity_type = 'reservation' AND entity_id = ?
                 AND action IN ('reservation_approved', 'reservation_expired')""",
            (reservation_id,),
        ).fetchone()["total"]
    assert state == "rejected_expired"
    assert events == 1


def test_approved_change_holds_both_intervals_until_approval(reservation_api):
    api = reservation_api
    original_start, original_end, _ = _future_interval(days=23)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=original_start.astimezone(timezone.utc),
        ends_at=original_end.astimezone(timezone.utc),
    )
    proposed_start, proposed_end, _ = _future_interval(days=25)

    response = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["starts_at_utc"] == original_start.astimezone(timezone.utc).isoformat()
    assert body["pending_change"]["starts_at_utc"] == proposed_start.astimezone(timezone.utc).isoformat(timespec="microseconds")
    duplicate_change = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": (proposed_start + timedelta(days=1)).isoformat(), "ends_at": (proposed_end + timedelta(days=1)).isoformat()},
    )
    assert duplicate_change.status_code == 409
    assert query_availability(
        space_id=api["space"]["id"], starts_at=original_start, ends_at=original_end
    )["availability"] == "occupied"
    assert query_availability(
        space_id=api["space"]["id"], starts_at=proposed_start, ends_at=proposed_end
    )["availability"] == "occupied"

    competing_reservation = api["client"].post(
        "/reservations", headers=api["other_requester_headers"],
        json={"space_id": api["space"]["id"], "starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    )
    assert competing_reservation.status_code == 409
    maintenance = api["client"].post(
        f"/spaces/{api['space']['id']}/maintenance-blocks",
        headers=api["admin_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat(), "reason": "Mantenimiento"},
    )
    assert maintenance.status_code == 409

    queue = api["client"].get("/approvals/pending-changes", headers=api["approver_headers"])
    assert queue.status_code == 200
    assert queue.json()[0]["reservation_id"] == reservation_id

    approved = api["client"].post(
        f"/approvals/change-requests/{body['pending_change']['id']}/decision",
        headers=api["approver_headers"], json={"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["starts_at_utc"] == proposed_start.astimezone(timezone.utc).isoformat(timespec="microseconds")
    assert approved.json()["pending_change"] is None
    assert query_availability(
        space_id=api["space"]["id"], starts_at=original_start, ends_at=original_end
    )["availability"] == "available"
    assert query_availability(
        space_id=api["space"]["id"], starts_at=proposed_start, ends_at=proposed_end
    )["availability"] == "occupied"


def test_rejected_approved_change_releases_provisional_interval(reservation_api):
    api = reservation_api
    original_start, original_end, _ = _future_interval(days=25)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=original_start.astimezone(timezone.utc),
        ends_at=original_end.astimezone(timezone.utc),
    )
    proposed_start, proposed_end, _ = _future_interval(days=26)
    changed = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    )
    change_id = changed.json()["pending_change"]["id"]

    no_reason = api["client"].post(
        f"/approvals/change-requests/{change_id}/decision",
        headers=api["approver_headers"], json={"decision": "reject", "reason": "  "},
    )
    assert no_reason.status_code == 422
    rejected = api["client"].post(
        f"/approvals/change-requests/{change_id}/decision",
        headers=api["approver_headers"], json={"decision": "reject", "reason": "Cambio no autorizado"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "approved"
    assert rejected.json()["starts_at_utc"] == original_start.astimezone(timezone.utc).isoformat()
    assert rejected.json()["pending_change"] is None
    assert query_availability(
        space_id=api["space"]["id"], starts_at=original_start, ends_at=original_end
    )["availability"] == "occupied"
    assert query_availability(
        space_id=api["space"]["id"], starts_at=proposed_start, ends_at=proposed_end
    )["availability"] == "available"


def test_cancelling_original_reservation_cancels_pending_change(reservation_api):
    api = reservation_api
    original_start, original_end, _ = _future_interval(days=27)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=original_start.astimezone(timezone.utc),
        ends_at=original_end.astimezone(timezone.utc),
    )
    proposed_start, proposed_end, _ = _future_interval(days=28)
    changed = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    )
    assert changed.status_code == 200

    cancelled = cancel_reservation(
        reservation_id=reservation_id,
        actor_user_id=api["requester"]["id"],
        actor_role="requester",
    )
    assert cancelled["status"] == "cancelled"
    with database_connection() as connection:
        change = connection.execute(
            "SELECT status FROM reservation_change_requests WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
    assert change["status"] == "cancelled"
    assert query_availability(
        space_id=api["space"]["id"], starts_at=proposed_start, ends_at=proposed_end
    )["availability"] == "available"


def test_pending_change_decision_requires_assigned_approver_who_is_not_requester(
    reservation_api,
):
    api = reservation_api
    original_start, original_end, _ = _future_interval(days=28)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=original_start.astimezone(timezone.utc),
        ends_at=original_end.astimezone(timezone.utc),
    )
    proposed_start, proposed_end, _ = _future_interval(days=29)
    change = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    ).json()["pending_change"]
    unassigned = _create_user(
        api["client"], api["admin_headers"], "otro.aprobador@universidad.edu.co", "approver"
    )
    unassigned_headers = _login(api["client"], "otro.aprobador@universidad.edu.co")
    assert api["client"].put(
        f"/permissions/spaces/{api['other_space']['id']}/approvers/{unassigned['id']}",
        headers=api["admin_headers"],
    ).status_code == 204
    assert api["client"].post(
        f"/approvals/change-requests/{change['id']}/decision",
        headers=unassigned_headers, json={"decision": "approve"},
    ).status_code == 403

    assert api["client"].patch(
        f"/users/{api['requester']['id']}/role", headers=api["admin_headers"],
        json={"role": "approver"},
    ).status_code == 200
    assert api["client"].put(
        f"/permissions/spaces/{api['space']['id']}/approvers/{api['requester']['id']}",
        headers=api["admin_headers"],
    ).status_code == 204
    owner_approver_headers = _login(api["client"], "solicitante@universidad.edu.co")
    assert api["client"].post(
        f"/approvals/change-requests/{change['id']}/decision",
        headers=owner_approver_headers, json={"decision": "approve"},
    ).status_code == 403
    with database_connection() as connection:
        assert connection.execute(
            "SELECT status FROM reservation_change_requests WHERE id = ?",
            (change["id"],),
        ).fetchone()["status"] == "pending"


def test_concurrent_decisions_resolve_a_pending_change_once(reservation_api):
    api = reservation_api
    original_start, original_end, _ = _future_interval(days=27)
    reservation_id = _insert_reservation(
        user_id=api["requester"]["id"], space_id=api["space"]["id"],
        status="approved", starts_at=original_start.astimezone(timezone.utc),
        ends_at=original_end.astimezone(timezone.utc),
    )
    proposed_start, proposed_end, _ = _future_interval(days=28)
    change = api["client"].put(
        f"/reservations/{reservation_id}", headers=api["requester_headers"],
        json={"starts_at": proposed_start.isoformat(), "ends_at": proposed_end.isoformat()},
    ).json()["pending_change"]
    second_approver = _create_user(
        api["client"], api["admin_headers"], "tercer.aprobador@universidad.edu.co", "approver"
    )
    assert api["client"].put(
        f"/permissions/spaces/{api['space']['id']}/approvers/{second_approver['id']}",
        headers=api["admin_headers"],
    ).status_code == 204
    second_headers = _login(api["client"], "tercer.aprobador@universidad.edu.co")
    url = f"/approvals/change-requests/{change['id']}/decision"

    def approve(headers):
        return api["client"].post(url, headers=headers, json={"decision": "approve"}).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        statuses = list(workers.map(approve, [api["approver_headers"], second_headers]))
    assert sorted(statuses) == [200, 409]
    with database_connection() as connection:
        change_status = connection.execute(
            "SELECT status FROM reservation_change_requests WHERE id = ?", (change["id"],)
        ).fetchone()["status"]
        event_count = connection.execute(
            """SELECT COUNT(*) AS total FROM history_events
               WHERE entity_type = 'reservation' AND entity_id = ?
                 AND action IN ('reservation_change_approved', 'reservation_change_rejected')""",
            (reservation_id,),
        ).fetchone()["total"]
    assert change_status == "approved"
    assert event_count == 1


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
