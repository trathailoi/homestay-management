"""Smoke tests for ORM model imports and table names."""

from app.models import Booking, Room, RoomAvailability


def test_room_model_exists():
    """Verify Room model loads and has correct table name."""
    assert Room.__tablename__ == "rooms"


def test_booking_model_exists():
    """Verify Booking model loads and has correct table name."""
    assert Booking.__tablename__ == "bookings"


def test_room_availability_model_exists():
    """Verify RoomAvailability model loads and has correct table name."""
    assert RoomAvailability.__tablename__ == "room_availability"
