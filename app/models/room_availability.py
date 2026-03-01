"""RoomAvailability ORM model."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.room import Room


class RoomAvailability(Base):
    """RoomAvailability model tracking daily availability for each room."""

    __tablename__ = "room_availability"
    __table_args__ = (
        PrimaryKeyConstraint("room_id", "date"),
        Index("ix_room_availability_date_available", "date", "is_available"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"),
        nullable=True,
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="availability")
    booking: Mapped["Booking | None"] = relationship(
        "Booking",
        back_populates="availability_dates",
    )
