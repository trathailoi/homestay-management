"""Tests for AvailabilityService date-range queries."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.room import RoomCreate
from app.services.availability_service import AvailabilityService
from app.services.room_service import RoomService


@pytest_asyncio.fixture
async def room_service(session: AsyncSession) -> RoomService:
    """Create a RoomService instance with the test session."""
    return RoomService(session)


@pytest_asyncio.fixture
async def availability_service(session: AsyncSession) -> AvailabilityService:
    """Create an AvailabilityService instance with the test session."""
    return AvailabilityService(session)


async def _create_test_room(
    room_service: RoomService,
    room_number: str,
    max_occupancy: int = 2,
) -> None:
    """Helper to create a test room with availability."""
    data = RoomCreate(
        room_number=room_number,
        room_type="standard",
        name=f"Room {room_number}",
        max_occupancy=max_occupancy,
        base_price_per_night=Decimal("100.00"),
    )
    await room_service.create_room(data)


@pytest.mark.asyncio
async def test_check_availability_returns_available_rooms(
    room_service: RoomService,
    availability_service: AvailabilityService,
) -> None:
    """Test that check_availability returns all available rooms."""
    # Create two rooms
    await _create_test_room(room_service, "101")
    await _create_test_room(room_service, "102")

    # Check availability for a future date range
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=3)

    available = await availability_service.check_availability(
        check_in=check_in,
        check_out=check_out,
        guests=1,
    )

    assert len(available) == 2
    room_numbers = {r["room_number"] for r in available}
    assert room_numbers == {"101", "102"}

    # Each result should have a total_price (3 nights * 100)
    for room in available:
        assert room["total_price"] == 300.0


@pytest.mark.asyncio
async def test_check_availability_filters_by_occupancy(
    room_service: RoomService,
    availability_service: AvailabilityService,
) -> None:
    """Test that check_availability filters by guest capacity."""
    # Create a room with max_occupancy=2
    await _create_test_room(room_service, "101", max_occupancy=2)
    # Create a room with max_occupancy=4
    await _create_test_room(room_service, "102", max_occupancy=4)

    # Check availability for 3 guests
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)

    available = await availability_service.check_availability(
        check_in=check_in,
        check_out=check_out,
        guests=3,
    )

    # Only the larger room should appear
    assert len(available) == 1
    assert available[0]["room_number"] == "102"
    assert available[0]["max_occupancy"] == 4


@pytest.mark.asyncio
async def test_get_room_calendar(
    room_service: RoomService,
    availability_service: AvailabilityService,
) -> None:
    """Test retrieving a room's availability calendar."""
    # Create a room
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Test Room",
        max_occupancy=2,
        base_price_per_night=Decimal("100.00"),
    )
    room = await room_service.create_room(data)

    # Get a 7-day calendar
    start_date = date.today()
    end_date = start_date + timedelta(days=6)

    calendar = await availability_service.get_room_calendar(
        room_id=room.id,
        start_date=start_date,
        end_date=end_date,
    )

    # Should have 7 days (inclusive)
    assert len(calendar) == 7

    # All should be available
    for day in calendar:
        assert day.is_available is True
        assert day.booking_id is None

    # Should be ordered by date
    dates = [day.date for day in calendar]
    assert dates == sorted(dates)
