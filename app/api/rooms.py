"""Rooms API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import ListResponse, Meta, RoomResponse, SuccessResponse
from app.schemas.room import RoomCreate, RoomUpdate
from app.services import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[RoomResponse]:
    """Create a new room."""
    service = RoomService(session)
    room = await service.create_room(data)
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.get("")
async def list_rooms(
    room_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_session),
) -> ListResponse[RoomResponse]:
    """List rooms with optional filtering."""
    service = RoomService(session)
    rooms, total = await service.list_rooms(
        room_type=room_type,
        status=status,
        page=page,
        per_page=per_page,
    )
    return ListResponse(
        data=[RoomResponse.model_validate(r) for r in rooms],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.get("/{room_id}")
async def get_room(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[RoomResponse]:
    """Get a room by ID."""
    service = RoomService(session)
    room = await service.get_room(room_id)
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.patch("/{room_id}")
async def update_room(
    room_id: UUID,
    data: RoomUpdate,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[RoomResponse]:
    """Update a room (partial update)."""
    service = RoomService(session)
    room = await service.update_room(room_id, data)
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.delete("/{room_id}")
async def delete_room(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[RoomResponse]:
    """Soft-delete a room (sets status to inactive)."""
    service = RoomService(session)
    room = await service.delete_room(room_id)
    return SuccessResponse(data=RoomResponse.model_validate(room))
