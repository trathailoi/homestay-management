"""Bookings API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.booking import BookingCreate, BookingResponse, BookingUpdate, CancelRequest
from app.schemas.common import ListResponse, Meta, SuccessResponse
from app.services import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Create a new booking."""
    service = BookingService(session)
    booking = await service.create_booking(data)
    return SuccessResponse(data=_booking_to_response(booking))


@router.get("")
async def list_bookings(
    status: str | None = None,
    room_id: UUID | None = None,
    check_in_from: date | None = None,
    check_in_to: date | None = None,
    guest_search: str | None = None,
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_session),
) -> ListResponse[BookingResponse]:
    """List bookings with optional filtering, guest search, and date range."""
    service = BookingService(session)
    bookings, total = await service.list_bookings(
        status=status,
        room_id=room_id,
        check_in_from=check_in_from,
        check_in_to=check_in_to,
        guest_search=guest_search,
        page=page,
        per_page=per_page,
    )
    return ListResponse(
        data=[_booking_to_response(b) for b in bookings],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.get("/{booking_id}")
async def get_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Get a booking by ID."""
    service = BookingService(session)
    booking = await service.get_booking(booking_id)
    return SuccessResponse(data=_booking_to_response(booking))


@router.patch("/{booking_id}")
async def update_booking(
    booking_id: UUID,
    data: BookingUpdate,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Update a booking (partial update)."""
    service = BookingService(session)
    booking = await service.update_booking(booking_id, data)
    return SuccessResponse(data=_booking_to_response(booking))


@router.post("/{booking_id}/confirm")
async def confirm_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Confirm a pending booking."""
    service = BookingService(session)
    booking = await service.confirm_booking(booking_id)
    return SuccessResponse(data=_booking_to_response(booking))


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: UUID,
    body: CancelRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Cancel a booking with optional reason."""
    service = BookingService(session)
    reason = body.reason if body else None
    booking = await service.cancel_booking(booking_id, reason)
    return SuccessResponse(data=_booking_to_response(booking))


@router.post("/{booking_id}/check-in")
async def check_in_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Check in a guest."""
    service = BookingService(session)
    booking = await service.check_in(booking_id)
    return SuccessResponse(data=_booking_to_response(booking))


@router.post("/{booking_id}/check-out")
async def check_out_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[BookingResponse]:
    """Check out a guest."""
    service = BookingService(session)
    booking = await service.check_out(booking_id)
    return SuccessResponse(data=_booking_to_response(booking))


def _booking_to_response(booking) -> BookingResponse:
    """Convert booking model to response, including room_number."""
    return BookingResponse(
        id=booking.id,
        room_id=booking.room_id,
        room_number=booking.room.room_number,
        guest_name=booking.guest_name,
        guest_phone=booking.guest_phone,
        check_in_date=booking.check_in_date,
        check_out_date=booking.check_out_date,
        num_guests=booking.num_guests,
        total_amount=booking.total_amount,
        status=booking.status,
        special_requests=booking.special_requests,
        idempotency_key=booking.idempotency_key,
        cancelled_at=booking.cancelled_at,
        cancellation_reason=booking.cancellation_reason,
        additional_fees=booking.additional_fees,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )
