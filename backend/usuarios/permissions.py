"""Role and reservation-scope checks used by protected operations."""

from dataclasses import dataclass


ADMINISTRATOR = "administrator"
REQUESTER = "requester"
APPROVER = "approver"


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str
    is_active: bool


def can_administer(principal: Principal) -> bool:
    return principal.is_active and principal.role == ADMINISTRATOR


def can_view_reservation(
    principal: Principal,
    *,
    owner_user_id: int,
    space_id: int,
    assigned_space_ids: set[int],
) -> bool:
    if not principal.is_active:
        return False
    if principal.role == ADMINISTRATOR:
        return True
    if principal.role == REQUESTER:
        return principal.user_id == owner_user_id
    return principal.role == APPROVER and space_id in assigned_space_ids


def can_change_reservation(
    principal: Principal,
    *,
    owner_user_id: int,
    space_id: int,
    assigned_space_ids: set[int],
) -> bool:
    if not principal.is_active:
        return False
    if principal.role == ADMINISTRATOR:
        return True
    if principal.role == REQUESTER:
        return principal.user_id == owner_user_id
    return principal.role == APPROVER and space_id in assigned_space_ids


def can_decide_reservation(
    principal: Principal,
    *,
    owner_user_id: int,
    space_id: int,
    assigned_space_ids: set[int],
) -> bool:
    return (
        principal.is_active
        and principal.role == APPROVER
        and principal.user_id != owner_user_id
        and space_id in assigned_space_ids
    )
