"""API tests for availability endpoints."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_availability(client: AsyncClient) -> None:
    """GET /api/v1/availability - returns available rooms with total_price."""
    # Create a room
    await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "AV01",
            "room_type": "standard",
            "name": "Garden View",
            "max_occupancy": 2,
            "base_price_per_night": 75.00,
        },
    )

    # Check availability for 3 nights
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=3)

    response = await client.get(
        "/api/v1/availability",
        params={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    room = data["data"][0]
    assert room["room_number"] == "AV01"
    # 3 nights * 75 = 225
    assert room["total_price"] == 225.00


@pytest.mark.asyncio
async def test_room_availability_calendar(client: AsyncClient) -> None:
    """GET /api/v1/availability/rooms/{id} - returns 7-day calendar."""
    # Create a room
    create_resp = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "102",
            "room_type": "deluxe",
            "name": "Ocean Suite",
            "max_occupancy": 4,
            "base_price_per_night": 150.00,
        },
    )
    room_id = create_resp.json()["data"]["id"]

    # Query 7-day calendar
    start_date = date.today()
    end_date = start_date + timedelta(days=6)

    response = await client.get(
        f"/api/v1/availability/rooms/{room_id}",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 7
    # All days should be available
    for day in data["data"]:
        assert day["is_available"] is True
        assert day["booking_id"] is None
