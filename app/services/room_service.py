"""Room service with CRUD operations and availability generation."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import RoomNotFoundError
from app.models import Room, RoomAvailability
from app.schemas.room import RoomCreate, RoomUpdate


class RoomService:
    """Service for managing rooms and their availability."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_room(self, data: RoomCreate) -> Room:
        """Create a new room and generate availability rows.

        Generates availability_window_days (default 365) days of availability
        starting from today.
        """
        room = Room(
            room_number=data.room_number,
            room_type=data.room_type,
            name=data.name,
            description=data.description,
            max_occupancy=data.max_occupancy,
            base_price_per_night=data.base_price_per_night,
            amenities=data.amenities,
        )
        self.session.add(room)
        await self.session.flush()  # Get room.id

        # Generate availability rows
        today = date.today()
        availability_rows = [
            RoomAvailability(
                room_id=room.id,
                date=today + timedelta(days=i),
                is_available=True,
            )
            for i in range(settings.availability_window_days)
        ]
        self.session.add_all(availability_rows)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def list_rooms(
        self,
        room_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Room], int]:
        """List rooms with optional filtering and pagination.

        When no status filter is provided, excludes inactive rooms by default.
        Results are ordered by room_number for consistent pagination.
        """
        query = select(Room)

        # Apply filters
        if room_type:
            query = query.where(Room.room_type == room_type)

        # Exclude inactive rooms by default
        if status:
            query = query.where(Room.status == status)
        else:
            query = query.where(Room.status != "inactive")

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query) or 0

        # Apply ordering and pagination
        query = query.order_by(Room.room_number)
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.session.execute(query)
        rooms = list(result.scalars().all())

        return rooms, total

    async def get_room(self, room_id: UUID) -> Room:
        """Get a room by ID.

        Raises RoomNotFoundError if not found.
        """
        room = await self.session.get(Room, room_id)
        if not room:
            raise RoomNotFoundError(str(room_id))
        return room

    async def update_room(self, room_id: UUID, data: RoomUpdate) -> Room:
        """Update a room with the provided fields.

        Only updates fields that are not None in the update data.
        Raises RoomNotFoundError if room not found.
        """
        room = await self.get_room(room_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(room, field, value)

        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def delete_room(self, room_id: UUID) -> Room:
        """Soft delete a room by setting status to 'inactive'.

        Raises RoomNotFoundError if room not found.
        """
        room = await self.get_room(room_id)
        room.status = "inactive"
        await self.session.commit()
        await self.session.refresh(room)
        return room
