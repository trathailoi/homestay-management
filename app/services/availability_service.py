"""Availability service with date-range queries."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Room, RoomAvailability


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

    async def check_all_rooms_availability(
        self,
        check_in: date,
        check_out: date,
        guests: int = 0,
    ) -> list[dict]:
        """Check availability of ALL non-inactive rooms for a date range.

        Returns every room with is_available flag, total_price for available
        rooms, and blocking booking details for unavailable rooms.
        """
        num_nights = (check_out - check_in).days
        if num_nights <= 0:
            return []

        dates_needed = [check_in + timedelta(days=i) for i in range(num_nights)]

        # Query 1: All non-inactive rooms, optionally filtered by capacity
        room_query = select(Room).where(Room.status != "inactive")
        if guests > 0:
            room_query = room_query.where(Room.max_occupancy >= guests)
        result = await self.session.execute(room_query)
        rooms = list(result.scalars().all())

        if not rooms:
            return []

        room_ids = [r.id for r in rooms]

        # Query 2: Count available dates per room in the range
        avail_count_query = (
            select(
                RoomAvailability.room_id,
                func.count().label("avail_count"),
            )
            .where(
                and_(
                    RoomAvailability.room_id.in_(room_ids),
                    RoomAvailability.date.in_(dates_needed),
                    RoomAvailability.is_available == True,  # noqa: E712
                )
            )
            .group_by(RoomAvailability.room_id)
        )
        avail_result = await self.session.execute(avail_count_query)
        avail_counts = {row.room_id: row.avail_count for row in avail_result}

        # Query 3: Blocking booking IDs for unavailable rooms
        unavailable_room_ids = [
            rid for rid in room_ids
            if avail_counts.get(rid, 0) < num_nights
        ]

        blocking_bookings_by_room: dict[UUID, list[dict]] = {
            rid: [] for rid in unavailable_room_ids
        }

        if unavailable_room_ids:
            blocking_query = (
                select(
                    RoomAvailability.room_id,
                    RoomAvailability.booking_id,
                )
                .where(
                    and_(
                        RoomAvailability.room_id.in_(unavailable_room_ids),
                        RoomAvailability.date.in_(dates_needed),
                        RoomAvailability.is_available == False,  # noqa: E712
                        RoomAvailability.booking_id.isnot(None),
                    )
                )
            )
            blocking_result = await self.session.execute(blocking_query)

            # Collect unique booking IDs per room
            booking_ids_per_room: dict[UUID, set[UUID]] = {
                rid: set() for rid in unavailable_room_ids
            }
            for row in blocking_result:
                booking_ids_per_room[row.room_id].add(row.booking_id)

            # Bulk load all blocking bookings
            all_booking_ids = set()
            for ids in booking_ids_per_room.values():
                all_booking_ids.update(ids)

            if all_booking_ids:
                bookings_query = select(Booking).where(
                    Booking.id.in_(all_booking_ids)
                )
                bookings_result = await self.session.execute(bookings_query)
                bookings_map = {
                    b.id: b for b in bookings_result.scalars().all()
                }

                for rid in unavailable_room_ids:
                    for bid in booking_ids_per_room[rid]:
                        b = bookings_map.get(bid)
                        if b:
                            blocking_bookings_by_room[rid].append({
                                "id": str(b.id),
                                "guest_name": b.guest_name,
                                "guest_phone": b.guest_phone,
                                "check_in_date": b.check_in_date,
                                "check_out_date": b.check_out_date,
                                "status": b.status,
                            })

        # Build response
        result_list = []
        for room in rooms:
            is_available = avail_counts.get(room.id, 0) >= num_nights
            total_price = (
                float(room.base_price_per_night * num_nights)
                if is_available
                else None
            )
            result_list.append({
                "id": str(room.id),
                "room_number": room.room_number,
                "room_type": room.room_type,
                "name": room.name,
                "max_occupancy": room.max_occupancy,
                "base_price_per_night": room.base_price_per_night,
                "amenities": room.amenities,
                "status": room.status,
                "is_available": is_available,
                "total_price": total_price,
                "blocking_bookings": blocking_bookings_by_room.get(room.id, []),
            })

        # Sort: available rooms first, then by room number
        result_list.sort(key=lambda r: (not r["is_available"], r["room_number"]))
        return result_list

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
