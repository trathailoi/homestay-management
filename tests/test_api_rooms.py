"""Tests for rooms API endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_room(client: AsyncClient) -> None:
    """Test room creation via API."""
    response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "101",
            "room_type": "standard",
            "name": "Garden View Room",
            "max_occupancy": 2,
            "base_price_per_night": 75.00,
            "amenities": ["wifi", "ac"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["room_number"] == "101"
    assert data["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_list_rooms(client: AsyncClient) -> None:
    """Test listing rooms via API."""
    # Create a room first
    await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "201",
            "room_type": "deluxe",
            "name": "Deluxe Room",
            "max_occupancy": 3,
            "base_price_per_night": 100.00,
        },
    )

    response = await client.get("/api/v1/rooms")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    assert "meta" in data
    assert data["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_room(client: AsyncClient) -> None:
    """Test getting a room by ID."""
    # Create a room
    create_response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "301",
            "room_type": "suite",
            "name": "Suite Room",
            "max_occupancy": 4,
            "base_price_per_night": 150.00,
        },
    )
    room_id = create_response.json()["data"]["id"]

    response = await client.get(f"/api/v1/rooms/{room_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["room_number"] == "301"


@pytest.mark.asyncio
async def test_get_room_not_found(client: AsyncClient) -> None:
    """Test getting a non-existent room returns 404."""
    random_id = str(uuid4())
    response = await client.get(f"/api/v1/rooms/{random_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ROOM_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_room(client: AsyncClient) -> None:
    """Test updating a room via PATCH."""
    # Create a room
    create_response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "401",
            "room_type": "standard",
            "name": "Standard Room",
            "max_occupancy": 2,
            "base_price_per_night": 75.00,
        },
    )
    room_id = create_response.json()["data"]["id"]

    # Update using PATCH
    response = await client.patch(
        f"/api/v1/rooms/{room_id}",
        json={"name": "Updated Room Name"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Updated Room Name"
    # Original fields should be unchanged
    assert data["data"]["room_number"] == "401"


@pytest.mark.asyncio
async def test_delete_room(client: AsyncClient) -> None:
    """Test soft-deleting a room sets status to inactive."""
    # Create a room
    create_response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "501",
            "room_type": "standard",
            "name": "To Delete",
            "max_occupancy": 2,
            "base_price_per_night": 50.00,
        },
    )
    room_id = create_response.json()["data"]["id"]

    response = await client.delete(f"/api/v1/rooms/{room_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "inactive"


@pytest.mark.asyncio
async def test_list_rooms_hides_inactive(client: AsyncClient) -> None:
    """Test that inactive rooms are hidden from default listing."""
    # Create and delete a room
    create_response = await client.post(
        "/api/v1/rooms",
        json={
            "room_number": "601",
            "room_type": "standard",
            "name": "Hidden Room",
            "max_occupancy": 2,
            "base_price_per_night": 50.00,
        },
    )
    room_id = create_response.json()["data"]["id"]
    await client.delete(f"/api/v1/rooms/{room_id}")

    # List without status filter - should not include the inactive room
    response = await client.get("/api/v1/rooms")
    rooms = response.json()["data"]
    room_ids = [r["id"] for r in rooms]

    assert room_id not in room_ids
