"""Tests for Pydantic schema validation."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.booking import BookingCreate, BookingUpdate, CancelRequest
from app.schemas.room import RoomCreate, RoomUpdate


class TestRoomSchemas:
    """Tests for room schema validation."""

    def test_room_create_valid(self):
        """Test creating a valid RoomCreate schema."""
        room = RoomCreate(
            room_number="101",
            room_type="standard",
            name="Garden View Room",
            description="A beautiful room",
            max_occupancy=2,
            base_price_per_night=Decimal("75.00"),
            amenities=["wifi", "ac"],
        )
        assert room.room_number == "101"
        assert room.room_type == "standard"
        assert room.base_price_per_night == Decimal("75.00")

    def test_room_create_minimal(self):
        """Test RoomCreate with only required fields."""
        room = RoomCreate(
            room_number="102",
            room_type="deluxe",
            name="Ocean View",
            max_occupancy=3,
            base_price_per_night=Decimal("150.00"),
        )
        assert room.description is None
        assert room.amenities is None

    def test_room_create_invalid_occupancy(self):
        """Test that negative occupancy raises validation error."""
        with pytest.raises(ValidationError):
            RoomCreate(
                room_number="103",
                room_type="standard",
                name="Test Room",
                max_occupancy=-1,
                base_price_per_night=Decimal("50.00"),
            )

    def test_room_create_invalid_price(self):
        """Test that negative price raises validation error."""
        with pytest.raises(ValidationError):
            RoomCreate(
                room_number="104",
                room_type="standard",
                name="Test Room",
                max_occupancy=2,
                base_price_per_night=Decimal("-10.00"),
            )

    def test_room_update_partial(self):
        """Test RoomUpdate accepts partial updates."""
        update = RoomUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.room_type is None
        assert update.status is None

    def test_room_update_status_validation(self):
        """Test RoomUpdate validates status values."""
        valid = RoomUpdate(status="active")
        assert valid.status == "active"

        with pytest.raises(ValidationError):
            RoomUpdate(status="invalid_status")


class TestBookingSchemas:
    """Tests for booking schema validation."""

    def test_booking_create_valid(self):
        """Test creating a valid BookingCreate schema."""
        booking = BookingCreate(
            room_id=uuid4(),
            guest_name="John Doe",
            guest_phone="+1234567890",
            check_in_date=date(2026, 3, 15),
            check_out_date=date(2026, 3, 18),
            num_guests=2,
            special_requests="Late checkout please",
        )
        assert booking.guest_name == "John Doe"
        assert booking.guest_phone == "+1234567890"
        assert booking.num_guests == 2

    def test_booking_create_requires_phone(self):
        """Test that guest_phone is required."""
        with pytest.raises(ValidationError):
            BookingCreate(
                room_id=uuid4(),
                guest_name="John Doe",
                # missing guest_phone
                check_in_date=date(2026, 3, 15),
                check_out_date=date(2026, 3, 18),
                num_guests=2,
            )

    def test_booking_create_invalid_guests(self):
        """Test that zero guests raises validation error."""
        with pytest.raises(ValidationError):
            BookingCreate(
                room_id=uuid4(),
                guest_name="John Doe",
                guest_phone="+1234567890",
                check_in_date=date(2026, 3, 15),
                check_out_date=date(2026, 3, 18),
                num_guests=0,
            )

    def test_booking_update_partial(self):
        """Test BookingUpdate accepts partial updates."""
        update = BookingUpdate(guest_name="Jane Doe")
        assert update.guest_name == "Jane Doe"
        assert update.guest_phone is None

    def test_cancel_request_optional_reason(self):
        """Test CancelRequest with and without reason."""
        with_reason = CancelRequest(reason="guest_request")
        assert with_reason.reason == "guest_request"

        without_reason = CancelRequest()
        assert without_reason.reason is None
