"""Pydantic schemas for API request/response models."""

from app.schemas.availability import (
    AvailabilityQuery,
    AvailableRoom,
    RoomAvailabilityDay,
)
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    CancelRequest,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    ListResponse,
    Meta,
    SuccessResponse,
)
from app.schemas.room import (
    RoomCreate,
    RoomResponse,
    RoomUpdate,
)

__all__ = [
    # Common
    "ErrorDetail",
    "ErrorResponse",
    "ListResponse",
    "Meta",
    "SuccessResponse",
    # Room
    "RoomCreate",
    "RoomResponse",
    "RoomUpdate",
    # Booking
    "BookingCreate",
    "BookingResponse",
    "BookingUpdate",
    "CancelRequest",
    # Availability
    "AvailabilityQuery",
    "AvailableRoom",
    "RoomAvailabilityDay",
]
