"""Pydantic schemas for booking API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class AdditionalFee(BaseModel):
    """Schema for an additional fee item.

    Valid types: early_checkin, late_checkout, other
    Amount can be 0 (fee waived as courtesy).
    Amount stored as string for JSON serialization.
    """

    model_config = {"ser_json_decimal": "str"}

    type: str
    description: str
    amount: Annotated[Decimal, Field(ge=0)]

    def model_dump(self, **kwargs):
        """Convert Decimal to string for JSON storage."""
        data = super().model_dump(**kwargs)
        data["amount"] = str(self.amount)
        return data


class BookingCreate(BaseModel):
    """Request body for creating a booking (POST /bookings)."""

    room_id: UUID
    guest_name: Annotated[str, Field(max_length=200)]
    guest_phone: Annotated[str, Field(max_length=50)]
    check_in_date: date
    check_out_date: date
    num_guests: Annotated[int, Field(gt=0)]
    special_requests: str | None = None
    idempotency_key: Annotated[str, Field(max_length=100)] | None = None


class BookingUpdate(BaseModel):
    """Request body for updating a booking (PATCH /bookings/{id} - partial update).

    Note: dates and room_id cannot be changed via update.
    Date changes require cancel + rebook (MVP limitation).
    """

    guest_name: Annotated[str, Field(max_length=200)] | None = None
    guest_phone: Annotated[str, Field(max_length=50)] | None = None
    special_requests: str | None = None
    num_guests: Annotated[int, Field(gt=0)] | None = None
    additional_fees: list[AdditionalFee] | None = None


class CancelRequest(BaseModel):
    """Request body for cancelling a booking (POST /bookings/{id}/cancel)."""

    reason: str | None = None


class BookingResponse(BaseModel):
    """Response body for booking endpoints."""

    model_config = {"from_attributes": True}

    id: UUID
    room_id: UUID
    room_number: str  # Eagerly loaded from room relationship
    guest_name: str
    guest_phone: str
    check_in_date: date
    check_out_date: date
    num_guests: int
    total_amount: Decimal
    status: str
    special_requests: str | None
    idempotency_key: str | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    additional_fees: list[dict] | None
    created_at: datetime
    updated_at: datetime
