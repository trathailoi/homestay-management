"""Custom exception classes for business logic errors."""


class HomestayError(Exception):
    """Base exception for all homestay business errors."""

    def __init__(self, message: str, code: str, details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class RoomNotFoundError(HomestayError):
    """Raised when a room cannot be found by ID."""

    def __init__(self, room_id: str, message: str | None = None):
        super().__init__(
            message=message or f"Room {room_id} not found",
            code="ROOM_NOT_FOUND",
            details={"room_id": room_id},
        )


class BookingNotFoundError(HomestayError):
    """Raised when a booking cannot be found by ID."""

    def __init__(self, booking_id: str, message: str | None = None):
        super().__init__(
            message=message or f"Booking {booking_id} not found",
            code="BOOKING_NOT_FOUND",
            details={"booking_id": booking_id},
        )


class RoomNotAvailableError(HomestayError):
    """Raised when a room is not available for requested dates."""

    def __init__(
        self,
        room_id: str,
        check_in: str,
        check_out: str,
        next_available_date: str | None = None,
    ):
        details = {
            "room_id": room_id,
            "check_in": check_in,
            "check_out": check_out,
        }
        if next_available_date:
            details["next_available_date"] = next_available_date

        super().__init__(
            message=f"Room {room_id} is not available from {check_in} to {check_out}",
            code="ROOM_NOT_AVAILABLE",
            details=details,
        )


class InvalidStatusTransitionError(HomestayError):
    """Raised when an invalid booking status transition is attempted."""

    def __init__(self, current_status: str, target_status: str, booking_id: str | None = None):
        details = {
            "current_status": current_status,
            "target_status": target_status,
        }
        if booking_id:
            details["booking_id"] = booking_id

        super().__init__(
            message=f"Cannot transition from {current_status} to {target_status}",
            code="INVALID_STATUS_TRANSITION",
            details=details,
        )


class BookingValidationError(HomestayError):
    """Base class for booking validation errors."""

    pass


class PastDateError(BookingValidationError):
    """Raised when check-in date is in the past."""

    def __init__(self, check_in: str):
        super().__init__(
            message=f"Check-in date {check_in} is in the past",
            code="PAST_DATE",
            details={"check_in": check_in},
        )


class OccupancyExceededError(BookingValidationError):
    """Raised when number of guests exceeds room capacity."""

    def __init__(self, num_guests: int, max_occupancy: int, room_id: str | None = None):
        details = {
            "num_guests": num_guests,
            "max_occupancy": max_occupancy,
        }
        if room_id:
            details["room_id"] = room_id

        super().__init__(
            message=f"Number of guests ({num_guests}) exceeds room capacity ({max_occupancy})",
            code="OCCUPANCY_EXCEEDED",
            details=details,
        )
