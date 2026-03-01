"""Pydantic schemas for room API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RoomCreate(BaseModel):
    """Request body for creating a room (POST /rooms)."""

    room_number: Annotated[str, Field(max_length=20, examples=["101"])]
    room_type: Annotated[str, Field(max_length=50, examples=["standard"])]
    name: Annotated[str, Field(max_length=100, examples=["Garden View Room"])]
    description: str | None = None
    max_occupancy: Annotated[int, Field(gt=0, examples=[2])]
    base_price_per_night: Annotated[Decimal, Field(gt=0, examples=[75.00])]
    amenities: list[str] | None = None


class RoomUpdate(BaseModel):
    """Request body for updating a room (PATCH /rooms/{id} - partial update)."""

    room_type: Annotated[str, Field(max_length=50)] | None = None
    name: Annotated[str, Field(max_length=100)] | None = None
    description: str | None = None
    max_occupancy: Annotated[int, Field(gt=0)] | None = None
    base_price_per_night: Annotated[Decimal, Field(gt=0)] | None = None
    amenities: list[str] | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of the allowed values."""
        if v is not None and v not in ("active", "maintenance", "inactive"):
            raise ValueError("status must be 'active', 'maintenance', or 'inactive'")
        return v


class RoomResponse(BaseModel):
    """Response body for room endpoints."""

    model_config = {"from_attributes": True}

    id: UUID
    room_number: str
    room_type: str
    name: str
    description: str | None
    max_occupancy: int
    base_price_per_night: float
    amenities: list[str] | None
    status: str
    created_at: datetime
    updated_at: datetime
