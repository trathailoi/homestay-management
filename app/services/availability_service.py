"""Availability service with date-range queries."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Room, RoomAvailability


class AvailabilityService:
    """Service for checking room availability."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_availability(
        self,
        check_in: date,
        check_out: date,
        guests: int = 1,
    ) -> list[dict]:
        """Find rooms available for all dates in the range.

        Returns rooms where:
        - ALL dates in [check_in, check_out) are available
        - max_occupancy >= guests
        - status = 'active'

        Returns list of dicts with room info and total_price.
        """
        num_nights = (check_out - check_in).days
        if num_nights <= 0:
            return []

        # Generate list of dates needed
        dates_needed = [check_in + timedelta(days=i) for i in range(num_nights)]

        # Subquery: find room_ids that have ALL dates available
        subquery = (
            select(RoomAvailability.room_id)
            .where(
                and_(
                    RoomAvailability.date.in_(dates_needed),
                    RoomAvailability.is_available == True,  # noqa: E712
                )
            )
            .group_by(RoomAvailability.room_id)
            .having(func.count() == num_nights)
        ).subquery()

        # Main query: get rooms that match subquery and capacity/status requirements
        query = select(Room).where(
            and_(
                Room.id.in_(select(subquery.c.room_id)),
                Room.max_occupancy >= guests,
                Room.status == "active",
            )
        )

        result = await self.session.execute(query)
        rooms = result.scalars().all()

        # Build response with total_price calculated
        available_rooms = []
        for room in rooms:
            total_price = float(room.base_price_per_night * num_nights)
            available_rooms.append({
                "id": str(room.id),
                "room_number": room.room_number,
                "room_type": room.room_type,
                "name": room.name,
                "max_occupancy": room.max_occupancy,
                "base_price_per_night": room.base_price_per_night,
                "amenities": room.amenities,
                "total_price": total_price,
            })

        return available_rooms

    async def get_room_calendar(
        self,
        room_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[RoomAvailability]:
        """Get availability calendar for a specific room.

        Returns ordered list of RoomAvailability objects for the date range.
        """
        query = (
            select(RoomAvailability)
            .where(
                and_(
                    RoomAvailability.room_id == room_id,
                    RoomAvailability.date >= start_date,
                    RoomAvailability.date <= end_date,
                )
            )
            .order_by(RoomAvailability.date)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
