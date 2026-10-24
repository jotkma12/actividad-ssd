"""Authentication, user administration, and approver assignment routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.usuarios.dependencies import (
    bearer_scheme,
    get_current_principal,
    require_administrator,
)
from backend.usuarios.permissions import Principal
from backend.usuarios.schemas import (
    AccountCreate,
    AccountRoleUpdate,
    AccountStatusResponse,
    AccountStatusUpdate,
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from backend.usuarios.service import (
    AccountConflictError,
    AccountNotFoundError,
    InvalidCredentialsError,
    assign_approver,
    authenticate,
    create_account,
    list_accounts,
    remove_approver,
    revoke_session,
    set_account_role,
    set_account_status,
)


router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse, tags=["authentication"])
def login(payload: LoginRequest) -> LoginResponse:
    try:
        token, user = authenticate(payload.institutional_email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos, o la cuenta está inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return LoginResponse(access_token=token, user=user)


@router.post(
    "/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["authentication"]
)
def logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    _principal: Annotated[Principal, Depends(get_current_principal)],
) -> Response:
    revoke_session(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
)
def create_user(
    payload: AccountCreate,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> UserResponse:
    try:
        return UserResponse(**create_account(**payload.model_dump()))
    except AccountConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None


@router.get("/users", response_model=list[UserResponse], tags=["users"])
def get_users(
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> list[UserResponse]:
    return [UserResponse(**user) for user in list_accounts()]


@router.patch(
    "/users/{user_id}/status",
    response_model=AccountStatusResponse,
    tags=["users"],
)
def update_user_status(
    user_id: int,
    payload: AccountStatusUpdate,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> AccountStatusResponse:
    try:
        user, future_reservations = set_account_status(user_id, payload.is_active)
    except AccountNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada") from None
    return AccountStatusResponse(
        user=user, future_reservations_to_review=future_reservations
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse, tags=["permissions"])
def update_user_role(
    user_id: int,
    payload: AccountRoleUpdate,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> UserResponse:
    try:
        return UserResponse(**set_account_role(user_id, payload.role))
    except AccountNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada") from None


@router.put(
    "/permissions/spaces/{space_id}/approvers/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["permissions"],
)
def add_space_approver(
    space_id: int,
    user_id: int,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> Response:
    try:
        assign_approver(space_id, user_id)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/permissions/spaces/{space_id}/approvers/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["permissions"],
)
def delete_space_approver(
    space_id: int,
    user_id: int,
    _principal: Annotated[Principal, Depends(require_administrator)],
) -> Response:
    try:
        remove_approver(space_id, user_id)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
