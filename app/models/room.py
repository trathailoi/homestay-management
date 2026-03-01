"""Room ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.room_availability import RoomAvailability


class Room(Base):
    """Room model representing a homestay room."""

    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    room_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_occupancy: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amenities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    availability: Mapped[list["RoomAvailability"]] = relationship(
        "RoomAvailability",
        back_populates="room",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="room",
    )
