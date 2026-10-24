"""Reservation query and cancellation routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.reservas.schemas import (
    CancellationRequest,
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from backend.reservas.service import (
    CancellationReasonRequiredError,
    ReservationConflictError,
    ReservationForbiddenError,
    ReservationNotFoundError,
    ReservationCreationForbiddenError,
    ReservationSpaceInactiveError,
    ReservationSpaceNotFoundError,
    ReservationContentionError,
    cancel_reservation,
    create_reservation,
    get_reservation,
    list_reservations,
    update_reservation,
)
from backend.usuarios.dependencies import get_current_principal
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: ReservationCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReservationResponse:
    try:
        return ReservationResponse(
            **create_reservation(
                user_id=principal.user_id,
                space_id=payload.space_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
            )
        )
    except ReservationCreationForbiddenError:
        raise HTTPException(status_code=403, detail="Solo solicitantes activos pueden crear reservas") from None
    except ReservationSpaceNotFoundError:
        raise HTTPException(status_code=404, detail="Espacio no encontrado") from None
    except ReservationSpaceInactiveError:
        raise HTTPException(status_code=409, detail="El espacio está inactivo") from None
    except ReservationConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ReservationContentionError:
        raise HTTPException(status_code=503, detail="No fue posible guardar por contención; intente nuevamente") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/{reservation_id}", response_model=ReservationResponse)
def update(
    reservation_id: int,
    payload: ReservationUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReservationResponse:
    if principal.role != "requester":
        raise HTTPException(status_code=403, detail="Solo el solicitante puede modificar sus reservas")
    try:
        return ReservationResponse(
            **update_reservation(
                reservation_id=reservation_id,
                actor_user_id=principal.user_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
            )
        )
    except ReservationNotFoundError:
        raise HTTPException(status_code=404, detail="Reserva no encontrada") from None
    except ReservationSpaceInactiveError:
        raise HTTPException(status_code=409, detail="El espacio está inactivo") from None
    except ReservationConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


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
