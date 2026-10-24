"""Authenticated space availability route."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.disponibilidad.schemas import AvailabilityResponse
from backend.disponibilidad.service import (
    AvailabilitySpaceNotFoundError,
    InactiveAvailabilitySpaceError,
    query_availability,
)
from backend.usuarios.dependencies import get_current_principal
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/spaces/{space_id}", response_model=AvailabilityResponse)
def check_space_availability(
    space_id: int,
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
    _principal: Annotated[Principal, Depends(get_current_principal)],
) -> AvailabilityResponse:
    try:
        return AvailabilityResponse(
            **query_availability(
                space_id=space_id,
                starts_at=starts_at,
                ends_at=ends_at,
            )
        )
    except AvailabilitySpaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio no encontrado",
        ) from None
    except InactiveAvailabilitySpaceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El espacio está desactivado y no acepta reservas",
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from None
