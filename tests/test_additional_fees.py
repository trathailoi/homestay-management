"""Tests for additional fees on bookings."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def create_test_room_and_booking(client: AsyncClient) -> tuple[str, str]:
    """Create a room and booking for testing. Returns (room_id, booking_id)."""
    # Create room
    response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "201",
            "room_type": "deluxe",
            "name": "Fee Test Room",
            "max_occupancy": 2,
            "base_price_per_night": 150.00,
        },
    )
    room_id = response.json()["data"]["id"]

    # Create booking
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)
    response = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Test Guest",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )
    booking_id = response.json()["data"]["id"]
    return room_id, booking_id


@pytest.mark.asyncio
async def test_add_additional_fees(client: AsyncClient) -> None:
    """PATCH booking with additional fees adds them correctly."""
    _, booking_id = await create_test_room_and_booking(client)

    fees = [
        {"type": "early_checkin", "description": "Early check-in at 10am", "amount": "25.00"},
        {"type": "late_checkout", "description": "Late check-out until 3pm", "amount": "0.00"},
    ]

    response = await client.patch(
        f"/api/v1/bookings/{booking_id}",
        json={"additional_fees": fees},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["additional_fees"] is not None
    assert len(data["data"]["additional_fees"]) == 2
    assert data["data"]["additional_fees"][0]["type"] == "early_checkin"
    assert data["data"]["additional_fees"][0]["amount"] == "25.00"
    assert data["data"]["additional_fees"][1]["type"] == "late_checkout"
    assert data["data"]["additional_fees"][1]["amount"] == "0.00"


@pytest.mark.asyncio
async def test_booking_response_includes_fees(client: AsyncClient) -> None:
    """GET booking returns additional_fees when present."""
    _, booking_id = await create_test_room_and_booking(client)

    # Add fees
    fees = [{"type": "other", "description": "Extra towels", "amount": "10.00"}]
    await client.patch(
        f"/api/v1/bookings/{booking_id}",
        json={"additional_fees": fees},
    )

    # GET booking
    response = await client.get(f"/api/v1/bookings/{booking_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["additional_fees"] is not None
    assert len(data["data"]["additional_fees"]) == 1
    assert data["data"]["additional_fees"][0]["description"] == "Extra towels"


@pytest.mark.asyncio
async def test_booking_without_fees_returns_null(client: AsyncClient) -> None:
    """GET booking returns null for additional_fees when none added."""
    _, booking_id = await create_test_room_and_booking(client)

    response = await client.get(f"/api/v1/bookings/{booking_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["additional_fees"] is None
