"""Tests for guest search functionality on bookings endpoint."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Room


@pytest.fixture
async def room_for_search(session: AsyncSession) -> Room:
    """Create a room for search tests."""
    room = Room(
        room_number="SEARCH-101",
        room_type="standard",
        name="Search Test Room",
        max_occupancy=2,
        base_price_per_night=100.00,
        amenities=["wifi"],
        status="active",
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


@pytest.fixture
async def bookings_for_search(
    session: AsyncSession, room_for_search: Room
) -> tuple[Booking, Booking]:
    """Create two bookings with different guests for search tests."""
    check_in = date.today() + timedelta(days=7)
    check_out = date.today() + timedelta(days=9)

    booking1 = Booking(
        room_id=room_for_search.id,
        guest_name="John Smith",
        guest_phone="+1-555-123-4567",
        check_in_date=check_in,
        check_out_date=check_out,
        num_guests=1,
        total_amount=200.00,
        idempotency_key=str(uuid4()),
        status="confirmed",
    )

    check_in2 = date.today() + timedelta(days=14)
    check_out2 = date.today() + timedelta(days=16)

    booking2 = Booking(
        room_id=room_for_search.id,
        guest_name="Jane Doe",
        guest_phone="+1-555-987-6543",
        check_in_date=check_in2,
        check_out_date=check_out2,
        num_guests=2,
        total_amount=200.00,
        idempotency_key=str(uuid4()),
        status="pending",
    )

    session.add_all([booking1, booking2])
    await session.commit()
    await session.refresh(booking1)
    await session.refresh(booking2)
    return booking1, booking2


@pytest.mark.asyncio
async def test_search_by_name(
    client: AsyncClient, bookings_for_search: tuple[Booking, Booking]
) -> None:
    """Test searching bookings by partial guest name."""
    booking1, _ = bookings_for_search

    # Search by partial name "John"
    response = await client.get("/api/v1/bookings", params={"guest_search": "John"})
    assert response.status_code == 200
    result = response.json()

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["guest_name"] == "John Smith"
    assert result["data"][0]["id"] == str(booking1.id)


@pytest.mark.asyncio
async def test_search_by_phone(
    client: AsyncClient, bookings_for_search: tuple[Booking, Booking]
) -> None:
    """Test searching bookings by phone number."""
    _, booking2 = bookings_for_search

    # Search by phone number
    response = await client.get("/api/v1/bookings", params={"guest_search": "987-6543"})
    assert response.status_code == 200
    result = response.json()

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["guest_name"] == "Jane Doe"
    assert result["data"][0]["id"] == str(booking2.id)


@pytest.mark.asyncio
async def test_search_no_match(
    client: AsyncClient, bookings_for_search: tuple[Booking, Booking]
) -> None:
    """Test searching for a guest that doesn't exist returns empty list."""
    response = await client.get(
        "/api/v1/bookings", params={"guest_search": "NonexistentGuest"}
    )
    assert response.status_code == 200
    result = response.json()

    assert result["success"] is True
    assert len(result["data"]) == 0


@pytest.mark.asyncio
async def test_search_case_insensitive(
    client: AsyncClient, bookings_for_search: tuple[Booking, Booking]
) -> None:
    """Test that search is case-insensitive."""
    booking1, _ = bookings_for_search

    # Search with different case
    response = await client.get("/api/v1/bookings", params={"guest_search": "SMITH"})
    assert response.status_code == 200
    result = response.json()

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["guest_name"] == "John Smith"
    assert result["data"][0]["id"] == str(booking1.id)
