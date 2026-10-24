"""Reservation query and cancellation routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.reservas.schemas import CancellationRequest, ReservationResponse
from backend.reservas.service import (
    CancellationReasonRequiredError,
    ReservationConflictError,
    ReservationForbiddenError,
    ReservationNotFoundError,
    cancel_reservation,
    get_reservation,
    list_reservations,
)
from backend.usuarios.dependencies import get_current_principal
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=list[ReservationResponse])
def query_reservations(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[ReservationResponse]:
    return [
        ReservationResponse(**reservation)
        for reservation in list_reservations(principal=principal)
    ]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def query_reservation(
    reservation_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReservationResponse:
    try:
        return ReservationResponse(
            **get_reservation(principal=principal, reservation_id=reservation_id)
        )
    except ReservationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada") from None


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel(
    reservation_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
    payload: CancellationRequest | None = None,
) -> ReservationResponse:
    try:
        return ReservationResponse(
            **cancel_reservation(
                reservation_id=reservation_id,
                actor_user_id=principal.user_id,
                actor_role=principal.role,
                reason=payload.reason if payload else None,
            )
        )
    except ReservationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada") from None
    except ReservationForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para cancelar esta reserva") from None
    except CancellationReasonRequiredError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El motivo es obligatorio para cancelaciones administrativas") from None
    except ReservationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
