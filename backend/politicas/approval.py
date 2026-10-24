"""Approval policy for the initial state of a new reservation."""

from typing import Literal


ReservationInitialStatus = Literal["pending", "approved"]


def initial_reservation_status(requires_approval: bool) -> ReservationInitialStatus:
    """Return the initial status using the space's current approval setting."""
    if not isinstance(requires_approval, bool):
        raise TypeError("requires_approval debe ser booleano")
    return "pending" if requires_approval else "approved"
