"""Read-only audit history endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.historial.schemas import HistoryEntityType, HistoryEventResponse
from backend.historial.service import (
    HistoryNotFoundError,
    InvalidHistoryFilterError,
    list_history,
)
from backend.usuarios.dependencies import get_current_principal
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryEventResponse])
def get_history(
    principal: Annotated[Principal, Depends(get_current_principal)],
    entity_type: HistoryEntityType | None = Query(default=None),
    entity_id: int | None = Query(default=None, gt=0),
) -> list[HistoryEventResponse]:
    try:
        return [
            HistoryEventResponse(**event)
            for event in list_history(
                principal=principal,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        ]
    except HistoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Historial no encontrado",
        ) from None
    except InvalidHistoryFilterError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El filtro de historial no es válido",
        ) from None
