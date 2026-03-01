"""Pydantic schemas for availability queries and responses."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class AvailabilityQuery(BaseModel):
    """Query parameters for availability search."""

    check_in: date
    check_out: date
    guests: Annotated[int, Field(default=1, gt=0)]


class RoomAvailabilityDay(BaseModel):
    """Single day in a room's availability calendar."""

    model_config = {"from_attributes": True}

    date: date
    is_available: bool
    booking_id: UUID | None = None


class AvailableRoom(BaseModel):
    """Room returned from availability search with total price for the stay.

    This is a projection focused on availability context, not the full room entity.
    """

    model_config = {"from_attributes": True}

    id: str
    room_number: str
    room_type: str
    name: str
    max_occupancy: int
    base_price_per_night: Decimal
    amenities: list[str] | None
    total_price: float  # Calculated: num_nights * base_price_per_night
