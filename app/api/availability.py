"""Availability API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import SuccessResponse
from app.schemas.availability import AvailableRoom, RoomAvailabilityDay
from app.services import AvailabilityService

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("")
async def check_availability(
    check_in: date = Query(..., description="Check-in date"),
    check_out: date = Query(..., description="Check-out date"),
    guests: int = Query(1, gt=0, description="Number of guests"),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[AvailableRoom]]:
    """Find available rooms for a date range."""
    service = AvailabilityService(session)
    rooms = await service.check_availability(check_in, check_out, guests)
    return SuccessResponse(
        data=[AvailableRoom.model_validate(r) for r in rooms]
    )


@router.get("/rooms/{room_id}")
async def get_room_calendar(
    room_id: UUID,
    start_date: date = Query(..., description="Calendar start date"),
    end_date: date = Query(..., description="Calendar end date"),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[RoomAvailabilityDay]]:
    """Get availability calendar for a specific room."""
    service = AvailabilityService(session)
    availability = await service.get_room_calendar(room_id, start_date, end_date)
    return SuccessResponse(
        data=[RoomAvailabilityDay.model_validate(a) for a in availability]
    )
