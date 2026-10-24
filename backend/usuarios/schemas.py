"""Request and response schemas for account and session endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.usuarios.security import (
    normalize_institutional_email,
    validate_password,
)


Role = Literal["administrator", "requester", "approver"]


class LoginRequest(BaseModel):
    institutional_email: str
    password: str

    @field_validator("institutional_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_institutional_email(value)


class AccountCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    institutional_email: str
    identification: str = Field(min_length=1, max_length=100)
    password: str
    role: Role

    @field_validator("full_name", "identification")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo es obligatorio")
        return value

    @field_validator("institutional_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_institutional_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        validate_password(value)
        return value


class AccountStatusUpdate(BaseModel):
    is_active: bool


class AccountRoleUpdate(BaseModel):
    role: Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    institutional_email: str
    identification: str | None
    role: Role
    is_active: bool
    created_at_utc: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class AccountStatusResponse(BaseModel):
    user: UserResponse
    future_reservations_to_review: int
