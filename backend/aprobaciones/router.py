"""Endpoints for assigned approval queues and reservation decisions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.aprobaciones.schemas import (
    PendingReservationChangeResponse,
    ReservationDecision,
)
from backend.aprobaciones.service import (
    ApprovalConflictError,
    ApprovalForbiddenError,
    ApprovalNotFoundError,
    ApprovalReasonRequiredError,
    decide_reservation,
    decide_reservation_change,
    list_pending_changes,
    list_pending_requests,
)
from backend.reservas.schemas import ReservationResponse
from backend.usuarios.dependencies import get_current_principal
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/pending", response_model=list[ReservationResponse])
def pending_requests(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[ReservationResponse]:
    try:
        return [
            ReservationResponse(**reservation)
            for reservation in list_pending_requests(principal=principal)
        ]
    except ApprovalForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un aprobador activo puede consultar esta bandeja",
        ) from None


@router.get(
    "/pending-changes",
    response_model=list[PendingReservationChangeResponse],
)
def pending_changes(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[PendingReservationChangeResponse]:
    try:
        return [
            PendingReservationChangeResponse(**change)
            for change in list_pending_changes(principal=principal)
        ]
    except ApprovalForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un aprobador activo puede consultar esta bandeja",
        ) from None


@router.post(
    "/reservations/{reservation_id}/decision",
    response_model=ReservationResponse,
)
def reservation_decision(
    reservation_id: int,
    payload: ReservationDecision,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReservationResponse:
    try:
        return ReservationResponse(
            **decide_reservation(
                reservation_id=reservation_id,
                principal=principal,
                decision=payload.decision,
                reason=payload.reason,
            )
        )
    except ApprovalForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para decidir esta solicitud",
        ) from None
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada",
        ) from None
    except ApprovalConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud ya fue resuelta o venció",
        ) from None
    except ApprovalReasonRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo es obligatorio para rechazar una solicitud",
        ) from None


@router.post(
    "/change-requests/{change_request_id}/decision",
    response_model=ReservationResponse,
)
def reservation_change_decision(
    change_request_id: int,
    payload: ReservationDecision,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReservationResponse:
    try:
        return ReservationResponse(
            **decide_reservation_change(
                change_request_id=change_request_id,
                principal=principal,
                decision=payload.decision,
                reason=payload.reason,
            )
        )
    except ApprovalForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para decidir este cambio",
        ) from None
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cambio no encontrado",
        ) from None
    except ApprovalConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cambio ya fue resuelto o su reserva dejó de estar aprobada",
        ) from None
    except ApprovalReasonRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo es obligatorio para rechazar un cambio",
        ) from None
