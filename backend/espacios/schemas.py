"""Request and response schemas for academic spaces."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(min_length=1, max_length=80)
    capacity: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=200)
    equipment: list[str] = Field(default_factory=list)
    is_active: bool
    requires_approval: bool

    @field_validator("name", "type", "location")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo es obligatorio")
        return value

    @field_validator("equipment")
    @classmethod
    def clean_equipment(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("Los nombres de los equipos no pueden estar vacíos")
        return cleaned


class SpaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(min_length=1, max_length=80)
    capacity: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=200)
    equipment: list[str] = Field(default_factory=list)

    @field_validator("name", "type", "location")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo es obligatorio")
        return value

    @field_validator("equipment")
    @classmethod
    def clean_equipment(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("Los nombres de los equipos no pueden estar vacíos")
        return cleaned


class SpaceStatusUpdate(BaseModel):
    is_active: bool


class SpaceResponse(BaseModel):
    id: int
    name: str
    type: str
    capacity: int
    location: str
    equipment: list[str]
    is_active: bool
    requires_approval: bool
    created_at_utc: str


class SpaceStatusResponse(BaseModel):
    space: SpaceResponse
    future_reservations_to_review: int


class MaintenanceBlockCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La descripción del motivo es obligatoria")
        return value


class MaintenanceBlockUpdate(MaintenanceBlockCreate):
    pass


class MaintenanceBlockResponse(BaseModel):
    id: int
    space_id: int
    starts_at_utc: str
    ends_at_utc: str
    reason: str
    created_at_utc: str
