"""Tests for BookingService lifecycle and conflict prevention."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    BookingNotFoundError,
    InvalidStatusTransitionError,
    PastDateError,
    RoomNotAvailableError,
)
from app.models import Booking, Room, RoomAvailability
from app.schemas.booking import BookingCreate, BookingUpdate
from app.schemas.room import RoomCreate
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.services.room_service import RoomService


@pytest_asyncio.fixture
async def room_service(session: AsyncSession) -> RoomService:
    """Create a RoomService instance."""
    return RoomService(session)


@pytest_asyncio.fixture
async def booking_service(session: AsyncSession) -> BookingService:
    """Create a BookingService instance."""
    return BookingService(session)


@pytest_asyncio.fixture
async def availability_service(session: AsyncSession) -> AvailabilityService:
    """Create an AvailabilityService instance."""
    return AvailabilityService(session)


@pytest_asyncio.fixture
async def test_room(room_service: RoomService) -> Room:
    """Create a test room for booking tests."""
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Test Room",
        max_occupancy=2,
        base_price_per_night=Decimal("100.00"),
    )
    return await room_service.create_room(data)


# Core Booking Tests


@pytest.mark.asyncio
async def test_create_booking(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test booking creation with correct status and total amount."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=3)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="John Doe",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=2,
    )

    booking = await booking_service.create_booking(data)

    assert booking.status == "pending"
    assert booking.total_amount == Decimal("300.00")  # 3 nights * 100
    assert booking.guest_name == "John Doe"
    assert booking.room_id == test_room.id


@pytest.mark.asyncio
async def test_create_booking_marks_dates_unavailable(
    booking_service: BookingService,
    availability_service: AvailabilityService,
    test_room: Room,
) -> None:
    """Test that creating a booking marks dates as unavailable."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Jane Doe",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    await booking_service.create_booking(data)

    # Check availability returns no rooms for the same dates
    available = await availability_service.check_availability(check_in, check_out, 1)
    assert len(available) == 0


@pytest.mark.asyncio
async def test_create_booking_conflict(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that overlapping bookings raise RoomNotAvailableError."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=3)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="First Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    await booking_service.create_booking(data)

    # Try to book overlapping dates
    data2 = BookingCreate(
        room_id=test_room.id,
        guest_name="Second Guest",
        guest_phone="+1234567891",
        check_in_date=check_in + timedelta(days=1),
        check_out_date=check_out,
        num_guests=1,
    )

    with pytest.raises(RoomNotAvailableError) as exc_info:
        await booking_service.create_booking(data2)

    assert exc_info.value.code == "ROOM_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_idempotent_booking(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that same idempotency_key returns same booking."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
        idempotency_key="unique-key-123",
    )

    booking1 = await booking_service.create_booking(data)
    booking2 = await booking_service.create_booking(data)

    assert booking1.id == booking2.id


@pytest.mark.asyncio
async def test_cancel_booking_releases_dates(
    booking_service: BookingService,
    availability_service: AvailabilityService,
    test_room: Room,
) -> None:
    """Test that cancelling a booking releases the dates."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    await booking_service.cancel_booking(booking.id)

    # Room should be available again
    available = await availability_service.check_availability(check_in, check_out, 1)
    assert len(available) == 1


# New from review


@pytest.mark.asyncio
async def test_create_booking_rejects_past_dates(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that booking with past check-in date raises PastDateError."""
    check_in = date.today() - timedelta(days=1)  # Yesterday
    check_out = date.today() + timedelta(days=1)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    with pytest.raises(PastDateError) as exc_info:
        await booking_service.create_booking(data)

    assert exc_info.value.code == "PAST_DATE"


@pytest.mark.asyncio
async def test_create_booking_allows_same_day(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that booking with today as check-in date succeeds."""
    check_in = date.today()
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    assert booking.check_in_date == check_in


@pytest.mark.asyncio
async def test_cancel_booking_records_reason(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that cancellation records reason and timestamp."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    cancelled = await booking_service.cancel_booking(booking.id, reason="guest_request")

    assert cancelled.cancelled_at is not None
    assert cancelled.cancellation_reason == "guest_request"


@pytest.mark.asyncio
async def test_check_in_rejects_early_date(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that check-in before check-in date fails."""
    check_in = date.today() + timedelta(days=5)  # 5 days from now
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    await booking_service.confirm_booking(booking.id)

    with pytest.raises(InvalidStatusTransitionError):
        await booking_service.check_in(booking.id)


# State Transitions


@pytest.mark.asyncio
async def test_confirm_booking(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test pending -> confirmed transition."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    confirmed = await booking_service.confirm_booking(booking.id)

    assert confirmed.status == "confirmed"


@pytest.mark.asyncio
async def test_check_in_booking(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test confirmed -> checked_in transition."""
    check_in = date.today()  # Same day check-in
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    await booking_service.confirm_booking(booking.id)
    checked_in = await booking_service.check_in(booking.id)

    assert checked_in.status == "checked_in"


@pytest.mark.asyncio
async def test_check_out_booking(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test checked_in -> checked_out transition."""
    check_in = date.today()
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    await booking_service.confirm_booking(booking.id)
    await booking_service.check_in(booking.id)
    checked_out = await booking_service.check_out(booking.id)

    assert checked_out.status == "checked_out"


@pytest.mark.asyncio
async def test_invalid_status_transition(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test that invalid transitions raise InvalidStatusTransitionError."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)

    # pending -> checked_in should fail (must confirm first)
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        await booking_service.check_in(booking.id)

    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


# Early Checkout


@pytest.mark.asyncio
async def test_early_checkout_releases_future_dates(
    booking_service: BookingService,
    availability_service: AvailabilityService,
    test_room: Room,
    session: AsyncSession,
) -> None:
    """Test that early checkout releases future dates."""
    check_in = date.today()
    check_out = check_in + timedelta(days=5)  # 5 night stay

    data = BookingCreate(
        room_id=test_room.id,
        guest_name="Guest",
        guest_phone="+1234567890",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
    )

    booking = await booking_service.create_booking(data)
    await booking_service.confirm_booking(booking.id)
    await booking_service.check_in(booking.id)
    await booking_service.check_out(booking.id)

    # Tomorrow should be available (early checkout releases future dates)
    tomorrow = date.today() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)
    available = await availability_service.check_availability(tomorrow, day_after, 1)
    assert len(available) == 1


# List Tests


@pytest.mark.asyncio
async def test_list_bookings(
    booking_service: BookingService, test_room: Room
) -> None:
    """Test listing multiple bookings."""
    for i in range(2):
        check_in = date.today() + timedelta(days=i * 10 + 1)
        check_out = check_in + timedelta(days=2)

        data = BookingCreate(
            room_id=test_room.id,
            guest_name=f"Guest {i}",
            guest_phone=f"+123456789{i}",
            check_in_date=check_in,
            check_out_date=check_out,
            num_guests=1,
        )
        await booking_service.create_booking(data)

    bookings, total = await booking_service.list_bookings()

    assert total == 2
    assert len(bookings) == 2
