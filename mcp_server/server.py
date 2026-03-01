"""MCP server for homestay management with 12 tools for AI agent integration.

Run with: python -m mcp_server.server
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastmcp import FastMCP

from app.database import SessionLocal
from app.exceptions import HomestayError
from app.schemas.booking import BookingCreate, BookingUpdate
from app.schemas.room import RoomCreate, RoomUpdate
from app.services import AvailabilityService, BookingService, RoomService

mcp = FastMCP("Homestay Management")


def _room_to_dict(room: Any) -> dict:
    """Convert a Room model to a dict for MCP response."""
    return {
        "id": str(room.id),
        "room_number": room.room_number,
        "room_type": room.room_type,
        "name": room.name,
        "description": room.description,
        "max_occupancy": room.max_occupancy,
        "base_price_per_night": float(room.base_price_per_night),
        "amenities": room.amenities,
        "status": room.status,
        "created_at": room.created_at.isoformat(),
        "updated_at": room.updated_at.isoformat(),
    }


def _booking_to_dict(booking: Any) -> dict:
    """Convert a Booking model to a dict for MCP response."""
    return {
        "id": str(booking.id),
        "room_id": str(booking.room_id),
        "room_number": booking.room.room_number,
        "guest_name": booking.guest_name,
        "guest_phone": booking.guest_phone,
        "check_in_date": booking.check_in_date.isoformat(),
        "check_out_date": booking.check_out_date.isoformat(),
        "num_guests": booking.num_guests,
        "total_amount": float(booking.total_amount),
        "status": booking.status,
        "special_requests": booking.special_requests,
        "idempotency_key": booking.idempotency_key,
        "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
        "cancellation_reason": booking.cancellation_reason,
        "created_at": booking.created_at.isoformat(),
        "updated_at": booking.updated_at.isoformat(),
    }


# ============================================================================
# ROOM MANAGEMENT TOOLS
# ============================================================================


@mcp.tool()
async def list_rooms(
    room_type: str | None = None,
    status: str | None = None,
) -> dict:
    """List all rooms with optional filtering.

    Use this to browse available room inventory. Results exclude inactive rooms
    by default unless status='inactive' is explicitly requested.

    Args:
        room_type: Filter by room type (e.g., 'standard', 'deluxe', 'suite')
        status: Filter by status ('active', 'maintenance', 'inactive')

    Returns:
        Dict with 'rooms' list and 'total' count. Each room includes
        id, room_number, room_type, name, max_occupancy, base_price_per_night,
        amenities, and status.
    """
    try:
        async with SessionLocal() as session:
            service = RoomService(session)
            rooms, total = await service.list_rooms(room_type=room_type, status=status)
            return {
                "rooms": [_room_to_dict(r) for r in rooms],
                "total": total,
            }
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def get_room(room_id: str) -> dict:
    """Get detailed information about a specific room.

    Use this to retrieve full room details including amenities and pricing
    before making a booking.

    Args:
        room_id: The UUID of the room to retrieve

    Returns:
        Room dict with full details, or error dict if not found.
    """
    try:
        async with SessionLocal() as session:
            service = RoomService(session)
            room = await service.get_room(UUID(room_id))
            return _room_to_dict(room)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def create_room(
    room_number: str,
    room_type: str,
    name: str,
    max_occupancy: int,
    base_price_per_night: float,
    description: str | None = None,
    amenities: list[str] | None = None,
) -> dict:
    """Create a new room in the inventory.

    Use this to add rooms to the system. Automatically generates 365 days
    of availability starting from today.

    Args:
        room_number: Unique room number (e.g., '101', '202A')
        room_type: Category like 'standard', 'deluxe', 'suite'
        name: Display name (e.g., 'Garden View Room')
        max_occupancy: Maximum number of guests
        base_price_per_night: Nightly rate in the system currency
        description: Optional detailed description
        amenities: Optional list of amenities like ['wifi', 'ac', 'minibar']

    Returns:
        Created room dict with assigned UUID and timestamps.
    """
    try:
        async with SessionLocal() as session:
            service = RoomService(session)
            data = RoomCreate(
                room_number=room_number,
                room_type=room_type,
                name=name,
                max_occupancy=max_occupancy,
                base_price_per_night=Decimal(str(base_price_per_night)),
                description=description,
                amenities=amenities,
            )
            room = await service.create_room(data)
            return _room_to_dict(room)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def update_room(
    room_id: str,
    room_type: str | None = None,
    name: str | None = None,
    max_occupancy: int | None = None,
    base_price_per_night: float | None = None,
    status: str | None = None,
) -> dict:
    """Update an existing room's information.

    Use this to modify room details. Only provided fields are updated;
    others remain unchanged (partial update).

    Args:
        room_id: The UUID of the room to update
        room_type: New room type category
        name: New display name
        max_occupancy: New maximum occupancy
        base_price_per_night: New nightly rate
        status: New status ('active', 'maintenance', 'inactive')

    Returns:
        Updated room dict, or error dict if not found.
    """
    try:
        async with SessionLocal() as session:
            service = RoomService(session)
            data = RoomUpdate(
                room_type=room_type,
                name=name,
                max_occupancy=max_occupancy,
                base_price_per_night=Decimal(str(base_price_per_night)) if base_price_per_night else None,
                status=status,
            )
            room = await service.update_room(UUID(room_id), data)
            return _room_to_dict(room)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


# ============================================================================
# AVAILABILITY TOOL
# ============================================================================


@mcp.tool()
async def check_availability(
    check_in: str,
    check_out: str,
    guests: int = 1,
) -> dict:
    """Find rooms available for a date range.

    Use this as the first step when making a booking. Returns rooms that are:
    - Available for ALL dates in the range
    - Have sufficient capacity for the guest count
    - Currently active (not in maintenance)

    Args:
        check_in: Check-in date in ISO format (YYYY-MM-DD)
        check_out: Check-out date in ISO format (YYYY-MM-DD)
        guests: Number of guests (default 1)

    Returns:
        Dict with 'available_rooms' list. Each room includes calculated
        'total_price' for the stay duration.
    """
    try:
        async with SessionLocal() as session:
            service = AvailabilityService(session)
            rooms = await service.check_availability(
                check_in=date.fromisoformat(check_in),
                check_out=date.fromisoformat(check_out),
                guests=guests,
            )
            return {"available_rooms": rooms}
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


# ============================================================================
# BOOKING LIFECYCLE TOOLS
# ============================================================================


@mcp.tool()
async def create_booking(
    room_id: str,
    guest_name: str,
    guest_phone: str,
    check_in_date: str,
    check_out_date: str,
    num_guests: int,
    special_requests: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Create a new booking reservation.

    Creates a booking in 'pending' status. Use confirm_booking to finalize.
    The idempotency_key allows safe retries - same key returns same booking.

    IMPORTANT: Check availability first with check_availability tool.

    Args:
        room_id: UUID of the room to book
        guest_name: Full name of the primary guest
        guest_phone: Contact phone number
        check_in_date: Check-in date (YYYY-MM-DD)
        check_out_date: Check-out date (YYYY-MM-DD)
        num_guests: Total number of guests
        special_requests: Optional notes (e.g., 'late check-in')
        idempotency_key: Optional unique key for safe retries

    Returns:
        Created booking dict with calculated total_amount and room_number,
        or error dict (ROOM_NOT_AVAILABLE, PAST_DATE, OCCUPANCY_EXCEEDED).
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            data = BookingCreate(
                room_id=UUID(room_id),
                guest_name=guest_name,
                guest_phone=guest_phone,
                check_in_date=date.fromisoformat(check_in_date),
                check_out_date=date.fromisoformat(check_out_date),
                num_guests=num_guests,
                special_requests=special_requests,
                idempotency_key=idempotency_key,
            )
            booking = await service.create_booking(data)
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def get_booking(booking_id: str) -> dict:
    """Get detailed information about a booking.

    Use this to check booking status, guest details, or total amount.

    Args:
        booking_id: The UUID of the booking to retrieve

    Returns:
        Booking dict with full details including room_number,
        or error dict if not found.
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            booking = await service.get_booking(UUID(booking_id))
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def list_bookings(
    status: str | None = None,
    room_id: str | None = None,
    check_in_from: str | None = None,
    check_in_to: str | None = None,
) -> dict:
    """List bookings with optional filtering.

    Use this to find bookings by status, room, or date range.
    Results are ordered by creation date (newest first).

    Args:
        status: Filter by status (pending, confirmed, checked_in, checked_out, cancelled)
        room_id: Filter by room UUID
        check_in_from: Filter check-in date >= this date (YYYY-MM-DD)
        check_in_to: Filter check-in date <= this date (YYYY-MM-DD)

    Returns:
        Dict with 'bookings' list and 'total' count.
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            bookings, total = await service.list_bookings(
                status=status,
                room_id=UUID(room_id) if room_id else None,
                check_in_from=date.fromisoformat(check_in_from) if check_in_from else None,
                check_in_to=date.fromisoformat(check_in_to) if check_in_to else None,
            )
            return {
                "bookings": [_booking_to_dict(b) for b in bookings],
                "total": total,
            }
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def confirm_booking(booking_id: str) -> dict:
    """Confirm a pending booking.

    Transitions booking from 'pending' to 'confirmed' status.
    Use this after payment is received or reservation is guaranteed.

    Args:
        booking_id: The UUID of the booking to confirm

    Returns:
        Updated booking dict with status='confirmed',
        or error dict (BOOKING_NOT_FOUND, INVALID_STATUS_TRANSITION).
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            booking = await service.confirm_booking(UUID(booking_id))
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def cancel_booking(
    booking_id: str,
    reason: str | None = None,
) -> dict:
    """Cancel a booking and release dates.

    Transitions booking from 'pending' or 'confirmed' to 'cancelled'.
    Releases the booked dates so the room becomes available again.

    Args:
        booking_id: The UUID of the booking to cancel
        reason: Optional cancellation reason for audit trail

    Returns:
        Updated booking dict with status='cancelled', cancelled_at timestamp,
        and cancellation_reason if provided.
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            booking = await service.cancel_booking(UUID(booking_id), reason=reason)
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def check_in(booking_id: str) -> dict:
    """Check in a guest for a confirmed booking.

    Transitions booking from 'confirmed' to 'checked_in'.
    Can only be done on or after the check-in date.

    Args:
        booking_id: The UUID of the booking to check in

    Returns:
        Updated booking dict with status='checked_in',
        or error dict if not yet check-in date or invalid status.
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            booking = await service.check_in(UUID(booking_id))
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


@mcp.tool()
async def check_out(booking_id: str) -> dict:
    """Check out a guest and complete the stay.

    Transitions booking from 'checked_in' to 'checked_out'.
    If checking out early, future dates are released for rebooking.

    Args:
        booking_id: The UUID of the booking to check out

    Returns:
        Updated booking dict with status='checked_out'.
    """
    try:
        async with SessionLocal() as session:
            service = BookingService(session)
            booking = await service.check_out(UUID(booking_id))
            return _booking_to_dict(booking)
    except HomestayError as e:
        return {"error": e.code, "message": e.message, "details": e.details}


if __name__ == "__main__":
    mcp.run()
