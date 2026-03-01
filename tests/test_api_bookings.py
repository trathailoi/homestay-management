"""API tests for bookings endpoints."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def create_test_room(client: AsyncClient, room_number: str = "101") -> str:
    """Helper to create a room and return its ID."""
    response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": room_number,
            "room_type": "standard",
            "name": "Test Room",
            "max_occupancy": 2,
            "base_price_per_night": 100.00,
        },
    )
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_booking(client: AsyncClient) -> None:
    """POST /api/v1/bookings - creates booking with correct status and total."""
    room_id = await create_test_room(client)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=3)

    response = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "John Doe",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 2,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "pending"
    assert float(data["data"]["total_amount"]) == 300.00  # 3 nights * 100
    assert data["data"]["room_number"] == "101"


@pytest.mark.asyncio
async def test_create_booking_conflict(client: AsyncClient) -> None:
    """POST /api/v1/bookings - overlapping dates return 409."""
    room_id = await create_test_room(client)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=3)

    # First booking succeeds
    await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "First Guest",
            "guest_phone": "+1111111111",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )

    # Second booking with overlapping dates fails
    response = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Second Guest",
            "guest_phone": "+2222222222",
            "check_in_date": (check_in + timedelta(days=1)).isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ROOM_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_create_booking_past_dates(client: AsyncClient) -> None:
    """POST /api/v1/bookings - past check-in date returns 400."""
    room_id = await create_test_room(client)
    check_in = date.today() - timedelta(days=1)  # Yesterday
    check_out = date.today() + timedelta(days=1)

    response = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Guest",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "PAST_DATE"


@pytest.mark.asyncio
async def test_get_booking(client: AsyncClient) -> None:
    """GET /api/v1/bookings/{id} - returns booking with room_number."""
    room_id = await create_test_room(client)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    create_resp = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Jane Doe",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )
    booking_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/bookings/{booking_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["guest_name"] == "Jane Doe"
    assert data["data"]["room_number"] == "101"


@pytest.mark.asyncio
async def test_list_bookings(client: AsyncClient) -> None:
    """GET /api/v1/bookings - lists bookings with total count."""
    room_id = await create_test_room(client)

    # Create 2 bookings with non-overlapping dates
    for i in range(2):
        check_in = date.today() + timedelta(days=i * 10 + 1)
        check_out = check_in + timedelta(days=2)
        await client.post(
            "/api/v1/bookings",
            json={
                "room_id": room_id,
                "guest_name": f"Guest {i}",
                "guest_phone": f"+123456789{i}",
                "check_in_date": check_in.isoformat(),
                "check_out_date": check_out.isoformat(),
                "num_guests": 1,
            },
        )

    response = await client.get("/api/v1/bookings")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["meta"]["total"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_list_bookings_date_filter(client: AsyncClient) -> None:
    """GET /api/v1/bookings - filter by check_in date range."""
    room_id = await create_test_room(client)

    # Booking 1: check-in in 5 days
    check_in_1 = date.today() + timedelta(days=5)
    await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Early Guest",
            "guest_phone": "+1111111111",
            "check_in_date": check_in_1.isoformat(),
            "check_out_date": (check_in_1 + timedelta(days=2)).isoformat(),
            "num_guests": 1,
        },
    )

    # Booking 2: check-in in 20 days
    check_in_2 = date.today() + timedelta(days=20)
    await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Late Guest",
            "guest_phone": "+2222222222",
            "check_in_date": check_in_2.isoformat(),
            "check_out_date": (check_in_2 + timedelta(days=2)).isoformat(),
            "num_guests": 1,
        },
    )

    # Filter to only get bookings with check-in in next 10 days
    filter_from = date.today()
    filter_to = date.today() + timedelta(days=10)

    response = await client.get(
        "/api/v1/bookings",
        params={
            "check_in_from": filter_from.isoformat(),
            "check_in_to": filter_to.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 1
    assert data["data"][0]["guest_name"] == "Early Guest"


@pytest.mark.asyncio
async def test_confirm_booking(client: AsyncClient) -> None:
    """POST /api/v1/bookings/{id}/confirm - changes status to confirmed."""
    room_id = await create_test_room(client)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    create_resp = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Guest",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )
    booking_id = create_resp.json()["data"]["id"]

    response = await client.post(f"/api/v1/bookings/{booking_id}/confirm")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_cancel_booking_with_reason(client: AsyncClient) -> None:
    """POST /api/v1/bookings/{id}/cancel - records cancellation reason."""
    room_id = await create_test_room(client)
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)

    create_resp = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Guest",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 1,
        },
    )
    booking_id = create_resp.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        json={"reason": "guest_request"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "cancelled"
    assert data["data"]["cancellation_reason"] == "guest_request"
    assert data["data"]["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_check_in_out_flow(client: AsyncClient) -> None:
    """Full lifecycle: create → confirm → check-in → check-out."""
    room_id = await create_test_room(client)
    check_in = date.today()  # Same-day check-in
    check_out = check_in + timedelta(days=2)

    # Create
    create_resp = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "guest_name": "Full Flow Guest",
            "guest_phone": "+1234567890",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "num_guests": 2,
        },
    )
    booking_id = create_resp.json()["data"]["id"]
    assert create_resp.json()["data"]["status"] == "pending"

    # Confirm
    confirm_resp = await client.post(f"/api/v1/bookings/{booking_id}/confirm")
    assert confirm_resp.json()["data"]["status"] == "confirmed"

    # Check-in
    checkin_resp = await client.post(f"/api/v1/bookings/{booking_id}/check-in")
    assert checkin_resp.json()["data"]["status"] == "checked_in"

    # Check-out
    checkout_resp = await client.post(f"/api/v1/bookings/{booking_id}/check-out")
    assert checkout_resp.json()["data"]["status"] == "checked_out"
