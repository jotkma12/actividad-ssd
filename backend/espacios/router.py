"""Academic space catalog routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.espacios.schemas import (
    SpaceCreate,
    MaintenanceBlockCreate,
    MaintenanceBlockResponse,
    MaintenanceBlockUpdate,
    SpaceResponse,
    SpaceStatusResponse,
    SpaceStatusUpdate,
    SpaceUpdate,
)
from backend.espacios.service import (
    SpaceNotFoundError,
    create_space,
    get_space,
    list_spaces,
    set_space_status,
    update_space,
)
from backend.espacios.maintenance import (
    MaintenanceBlockNotFoundError,
    MaintenanceConflictError,
    create_maintenance_block,
    delete_maintenance_block,
    list_maintenance_blocks,
    update_maintenance_block,
)
from backend.usuarios.dependencies import require_administrator
from backend.usuarios.permissions import Principal


router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=list[SpaceResponse])
def query_spaces() -> list[SpaceResponse]:
    return [SpaceResponse(**space) for space in list_spaces()]


@router.get("/{space_id}", response_model=SpaceResponse)
def query_space(space_id: int) -> SpaceResponse:
    try:
        return SpaceResponse(**get_space(space_id))
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None


@router.post(
    "",
    response_model=SpaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_space(
    payload: SpaceCreate,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> SpaceResponse:
    return SpaceResponse(
        **create_space(actor_user_id=principal.user_id, **payload.model_dump())
    )


@router.put("/{space_id}", response_model=SpaceResponse)
def edit_space(
    space_id: int,
    payload: SpaceUpdate,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> SpaceResponse:
    try:
        return SpaceResponse(
            **update_space(
                actor_user_id=principal.user_id,
                space_id=space_id,
                **payload.model_dump(),
            )
        )
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None


@router.patch("/{space_id}/status", response_model=SpaceStatusResponse)
def change_space_status(
    space_id: int,
    payload: SpaceStatusUpdate,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> SpaceStatusResponse:
    try:
        space, future_reservations = set_space_status(
            actor_user_id=principal.user_id,
            space_id=space_id,
            is_active=payload.is_active,
        )
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None
    return SpaceStatusResponse(
        space=space, future_reservations_to_review=future_reservations
    )


@router.get(
    "/{space_id}/maintenance-blocks",
    response_model=list[MaintenanceBlockResponse],
)
def query_maintenance_blocks(
    space_id: int,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> list[MaintenanceBlockResponse]:
    try:
        return [
            MaintenanceBlockResponse(**block)
            for block in list_maintenance_blocks(space_id)
        ]
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None


@router.post(
    "/{space_id}/maintenance-blocks",
    response_model=MaintenanceBlockResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_maintenance_block(
    space_id: int,
    payload: MaintenanceBlockCreate,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> MaintenanceBlockResponse:
    try:
        block = create_maintenance_block(
            actor_user_id=principal.user_id,
            space_id=space_id,
            **payload.model_dump(),
        )
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None
    except MaintenanceConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(error), "reservations": error.reservations},
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None
    return MaintenanceBlockResponse(**block)


@router.put(
    "/{space_id}/maintenance-blocks/{block_id}",
    response_model=MaintenanceBlockResponse,
)
def edit_maintenance_block(
    space_id: int,
    block_id: int,
    payload: MaintenanceBlockUpdate,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> MaintenanceBlockResponse:
    try:
        block = update_maintenance_block(
            actor_user_id=principal.user_id,
            space_id=space_id,
            block_id=block_id,
            **payload.model_dump(),
        )
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None
    except MaintenanceBlockNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bloqueo no encontrado") from None
    except MaintenanceConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(error), "reservations": error.reservations},
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None
    return MaintenanceBlockResponse(**block)


@router.delete(
    "/{space_id}/maintenance-blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_maintenance_block(
    space_id: int,
    block_id: int,
    principal: Annotated[Principal, Depends(require_administrator)],
) -> Response:
    try:
        delete_maintenance_block(
            actor_user_id=principal.user_id,
            space_id=space_id,
            block_id=block_id,
        )
    except SpaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado") from None
    except MaintenanceBlockNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bloqueo no encontrado") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
