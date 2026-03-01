"""Tests for RoomService CRUD operations and availability generation."""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import RoomNotFoundError
from app.models import Room, RoomAvailability
from app.schemas.room import RoomCreate, RoomUpdate
from app.services.room_service import RoomService


@pytest_asyncio.fixture
async def room_service(session: AsyncSession) -> RoomService:
    """Create a RoomService instance with the test session."""
    return RoomService(session)


@pytest.mark.asyncio
async def test_create_room(room_service: RoomService) -> None:
    """Test room creation with correct fields and default status."""
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Garden View Room",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
        amenities=["wifi", "ac"],
    )

    room = await room_service.create_room(data)

    assert room.room_number == "101"
    assert room.room_type == "standard"
    assert room.name == "Garden View Room"
    assert room.max_occupancy == 2
    assert room.base_price_per_night == Decimal("75.00")
    assert room.amenities == ["wifi", "ac"]
    assert room.status == "active"


@pytest.mark.asyncio
async def test_list_rooms(room_service: RoomService, session: AsyncSession) -> None:
    """Test listing rooms returns all rooms with correct total."""
    # Create two rooms
    for num in ["101", "102"]:
        data = RoomCreate(
            room_number=num,
            room_type="standard",
            name=f"Room {num}",
            max_occupancy=2,
            base_price_per_night=Decimal("75.00"),
        )
        await room_service.create_room(data)

    rooms, total = await room_service.list_rooms()

    assert total == 2
    assert len(rooms) == 2


@pytest.mark.asyncio
async def test_get_room(room_service: RoomService) -> None:
    """Test getting a room by ID returns correct data."""
    data = RoomCreate(
        room_number="101",
        room_type="deluxe",
        name="Test Room",
        max_occupancy=3,
        base_price_per_night=Decimal("100.00"),
    )
    created = await room_service.create_room(data)

    room = await room_service.get_room(created.id)

    assert room.id == created.id
    assert room.room_number == "101"
    assert room.room_type == "deluxe"


@pytest.mark.asyncio
async def test_get_room_not_found(room_service: RoomService) -> None:
    """Test getting a nonexistent room raises RoomNotFoundError."""
    random_id = uuid4()

    with pytest.raises(RoomNotFoundError) as exc_info:
        await room_service.get_room(random_id)

    assert exc_info.value.code == "ROOM_NOT_FOUND"
    assert str(random_id) in exc_info.value.details.get("room_id", "")


@pytest.mark.asyncio
async def test_update_room(room_service: RoomService) -> None:
    """Test updating a room persists changes."""
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Original Name",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
    )
    created = await room_service.create_room(data)

    update_data = RoomUpdate(name="Updated Name")
    updated = await room_service.update_room(created.id, update_data)

    assert updated.name == "Updated Name"
    assert updated.room_type == "standard"  # Unchanged


@pytest.mark.asyncio
async def test_delete_room_sets_inactive(room_service: RoomService) -> None:
    """Test soft-deleting a room sets status to inactive."""
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Test Room",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
    )
    created = await room_service.create_room(data)
    assert created.status == "active"

    deleted = await room_service.delete_room(created.id)

    assert deleted.status == "inactive"


@pytest.mark.asyncio
async def test_create_room_generates_availability(
    room_service: RoomService, session: AsyncSession
) -> None:
    """Test room creation generates availability rows for the configured window."""
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Test Room",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
    )
    room = await room_service.create_room(data)

    # Count availability rows for this room
    result = await session.execute(
        select(RoomAvailability).where(RoomAvailability.room_id == room.id)
    )
    availability_rows = list(result.scalars().all())

    assert len(availability_rows) == settings.availability_window_days


@pytest.mark.asyncio
async def test_list_rooms_excludes_inactive_by_default(
    room_service: RoomService,
) -> None:
    """Test that inactive rooms are excluded from default listing."""
    # Create a room
    data = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Test Room",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
    )
    room = await room_service.create_room(data)

    # Soft-delete it
    await room_service.delete_room(room.id)

    # List without filter - should be empty
    rooms, total = await room_service.list_rooms()
    assert total == 0
    assert len(rooms) == 0

    # List with explicit inactive filter - should return 1
    rooms, total = await room_service.list_rooms(status="inactive")
    assert total == 1
    assert len(rooms) == 1


@pytest.mark.asyncio
async def test_list_rooms_ordered_by_room_number(room_service: RoomService) -> None:
    """Test that room listing is ordered by room_number."""
    # Create rooms in non-alphabetical order
    for num in ["201", "101", "301"]:
        data = RoomCreate(
            room_number=num,
            room_type="standard",
            name=f"Room {num}",
            max_occupancy=2,
            base_price_per_night=Decimal("75.00"),
        )
        await room_service.create_room(data)

    rooms, _ = await room_service.list_rooms()

    # Should be ordered 101, 201, 301
    room_numbers = [r.room_number for r in rooms]
    assert room_numbers == ["101", "201", "301"]
