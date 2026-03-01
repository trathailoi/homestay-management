"""Booking service with lifecycle management and conflict prevention."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    BookingNotFoundError,
    BookingValidationError,
    InvalidStatusTransitionError,
    OccupancyExceededError,
    PastDateError,
    RoomNotAvailableError,
    RoomNotFoundError,
)
from app.models import Booking, Room, RoomAvailability
from app.schemas.booking import BookingCreate, BookingUpdate


# Valid state transitions for booking status
VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["checked_in", "cancelled"],
    "checked_in": ["checked_out"],
    "checked_out": [],
    "cancelled": [],
}


class BookingService:
    """Service for managing bookings with lifecycle and availability control."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_booking(self, data: BookingCreate) -> Booking:
        """Create a new booking with atomic availability locking.

        This is the most critical operation - must be atomic and conflict-free.
        """
        # Check idempotency key - if exists, return existing booking
        if data.idempotency_key:
            result = await self.session.execute(
                select(Booking).where(Booking.idempotency_key == data.idempotency_key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Validate check_in_date is not in the past
        today = date.today()
        if data.check_in_date < today:
            raise PastDateError(str(data.check_in_date))

        # Validate check_out > check_in
        num_nights = (data.check_out_date - data.check_in_date).days
        if num_nights <= 0:
            raise BookingValidationError(
                message="Check-out date must be after check-in date",
                code="INVALID_DATES",
                details={
                    "check_in_date": str(data.check_in_date),
                    "check_out_date": str(data.check_out_date),
                },
            )

        # Get the room
        room = await self.session.get(Room, data.room_id)
        if not room:
            raise RoomNotFoundError(str(data.room_id))

        # Validate occupancy
        if data.num_guests > room.max_occupancy:
            raise OccupancyExceededError(
                num_guests=data.num_guests,
                max_occupancy=room.max_occupancy,
                room_id=str(data.room_id),
            )

        # Calculate dates needed
        dates_needed = [
            data.check_in_date + timedelta(days=i) for i in range(num_nights)
        ]

        # Query availability rows with locking (only on PostgreSQL)
        query = select(RoomAvailability).where(
            and_(
                RoomAvailability.room_id == data.room_id,
                RoomAvailability.date.in_(dates_needed),
                RoomAvailability.is_available == True,  # noqa: E712
            )
        )

        # Use FOR UPDATE only on PostgreSQL (SQLite doesn't support it)
        bind = self.session.get_bind()
        if bind and hasattr(bind, "dialect") and bind.dialect.name != "sqlite":
            query = query.with_for_update()

        result = await self.session.execute(query)
        available_rows = list(result.scalars().all())

        # Check if all dates are available
        if len(available_rows) != num_nights:
            # Find next available date for error message
            next_available = await self._find_next_available_date(
                data.room_id, data.check_out_date
            )
            raise RoomNotAvailableError(
                room_id=str(data.room_id),
                check_in=str(data.check_in_date),
                check_out=str(data.check_out_date),
                next_available_date=str(next_available) if next_available else None,
            )

        # Calculate total amount using Decimal arithmetic
        total_amount = Decimal(str(room.base_price_per_night)) * num_nights

        # Create booking
        booking = Booking(
            room_id=data.room_id,
            guest_name=data.guest_name,
            guest_phone=data.guest_phone,
            check_in_date=data.check_in_date,
            check_out_date=data.check_out_date,
            num_guests=data.num_guests,
            total_amount=total_amount,
            status="pending",
            special_requests=data.special_requests,
            idempotency_key=data.idempotency_key,
        )
        self.session.add(booking)
        await self.session.flush()

        # Mark availability rows as booked
        for row in available_rows:
            row.is_available = False
            row.booking_id = booking.id

        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def _find_next_available_date(
        self, room_id: UUID, start_from: date
    ) -> date | None:
        """Find the next available date for a room starting from a given date."""
        result = await self.session.execute(
            select(RoomAvailability.date)
            .where(
                and_(
                    RoomAvailability.room_id == room_id,
                    RoomAvailability.date >= start_from,
                    RoomAvailability.is_available == True,  # noqa: E712
                )
            )
            .order_by(RoomAvailability.date)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row else None

    async def get_booking(self, booking_id: UUID) -> Booking:
        """Get a booking by ID.

        Raises BookingNotFoundError if not found.
        """
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            raise BookingNotFoundError(str(booking_id))
        return booking

    async def list_bookings(
        self,
        status: str | None = None,
        room_id: UUID | None = None,
        check_in_from: date | None = None,
        check_in_to: date | None = None,
        guest_search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Booking], int]:
        """List bookings with optional filtering and pagination.

        Results are ordered by created_at DESC for consistent pagination.
        """
        query = select(Booking)

        # Apply filters
        if status:
            query = query.where(Booking.status == status)
        if room_id:
            query = query.where(Booking.room_id == room_id)
        if check_in_from:
            query = query.where(Booking.check_in_date >= check_in_from)
        if check_in_to:
            query = query.where(Booking.check_in_date <= check_in_to)
        if guest_search:
            # Case-insensitive partial match on guest name or phone
            pattern = f"%{guest_search}%"
            from sqlalchemy import or_
            query = query.where(
                or_(
                    Booking.guest_name.ilike(pattern),
                    Booking.guest_phone.ilike(pattern),
                )
            )

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query) or 0

        # Apply ordering and pagination
        query = query.order_by(Booking.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.session.execute(query)
        bookings = list(result.scalars().all())

        return bookings, total

    async def update_booking(
        self, booking_id: UUID, data: BookingUpdate
    ) -> Booking:
        """Update booking fields.

        Cannot modify cancelled or checked_out bookings.
        """
        booking = await self.get_booking(booking_id)

        # Cannot update completed bookings
        if booking.status in ("cancelled", "checked_out"):
            raise InvalidStatusTransitionError(
                current_status=booking.status,
                target_status="update",
                booking_id=str(booking_id),
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Convert Decimal to string in additional_fees for JSON serialization
            if field == "additional_fees" and value is not None:
                value = [
                    {**fee, "amount": str(fee["amount"])}
                    for fee in value
                ]
            setattr(booking, field, value)

        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def _transition(self, booking_id: UUID, new_status: str) -> Booking:
        """Validate and execute status transition.

        Raises InvalidStatusTransitionError if transition is not allowed.
        """
        booking = await self.get_booking(booking_id)
        current_status = booking.status

        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                current_status=current_status,
                target_status=new_status,
                booking_id=str(booking_id),
            )

        booking.status = new_status
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def confirm_booking(self, booking_id: UUID) -> Booking:
        """Confirm a pending booking: pending -> confirmed."""
        return await self._transition(booking_id, "confirmed")

    async def cancel_booking(
        self, booking_id: UUID, reason: str | None = None
    ) -> Booking:
        """Cancel a booking: pending/confirmed -> cancelled.

        Releases the booked availability dates.
        """
        booking = await self._transition(booking_id, "cancelled")

        # Set cancellation metadata
        booking.cancelled_at = datetime.now(timezone.utc)
        booking.cancellation_reason = reason

        # Release availability
        await self.session.execute(
            update(RoomAvailability)
            .where(RoomAvailability.booking_id == booking_id)
            .values(is_available=True, booking_id=None)
        )

        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def check_in(self, booking_id: UUID) -> Booking:
        """Check in a guest: confirmed -> checked_in.

        Cannot check in before the check-in date.
        """
        booking = await self.get_booking(booking_id)

        # Validate date
        if date.today() < booking.check_in_date:
            raise InvalidStatusTransitionError(
                current_status=booking.status,
                target_status="checked_in",
                booking_id=str(booking_id),
            )

        return await self._transition(booking_id, "checked_in")

    async def check_out(self, booking_id: UUID) -> Booking:
        """Check out a guest: checked_in -> checked_out.

        Releases any future availability dates (for early checkout).
        """
        booking = await self._transition(booking_id, "checked_out")

        # Release future dates (early checkout handling)
        today = date.today()
        await self.session.execute(
            update(RoomAvailability)
            .where(
                and_(
                    RoomAvailability.booking_id == booking_id,
                    RoomAvailability.date > today,
                )
            )
            .values(is_available=True, booking_id=None)
        )

        await self.session.commit()
        await self.session.refresh(booking)
        return booking
