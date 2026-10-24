"""Authentication dependencies for protected API routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.usuarios.permissions import Principal, can_administer
from backend.usuarios.service import get_user_for_session


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere una sesión activa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_for_session(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida o la cuenta está inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(
        user_id=user["id"], role=user["role"], is_active=user["is_active"]
    )


def require_administrator(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not can_administer(principal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere el rol de administrador",
        )
    return principal
