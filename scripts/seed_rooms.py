#!/usr/bin/env python3
"""Replace all sample data with the real View Biển homestay rooms.

Run:
  docker compose exec -e PYTHONPATH=/app backend python scripts/seed_rooms.py

This is destructive by design: it wipes the demo bookings and sample rooms
(seeded by seed_data.py) and inserts the 5 real rooms. User accounts are left
untouched. Prices are in Vietnamese đồng (VND); base_price_per_night holds the
"from" (low-season) rate, the weekend/peak ceiling is noted in the description.

Source: View Biển homestay flyer, Làng Chài Ninh Vân (Cô Đào – 0355.329.669).
"""

import asyncio
from decimal import Decimal

from sqlalchemy import delete

from app.database import SessionLocal
from app.models import Booking, Room, RoomAvailability
from app.schemas.room import RoomCreate
from app.services.room_service import RoomService

AMENITIES = [
    "View biển trực diện",
    "Chỗ đậu ô tô có mái che",
    "Bếp riêng & dụng cụ nấu ăn",
    "Đầy đủ tiện nghi sinh hoạt",
    "Gần biển, không gian thoáng mát",
]

ROOMS = [
    RoomCreate(
        room_number="101",
        room_type="double",
        name="Phòng Đôi View Biển 1",
        description="Phòng đôi 2 giường 1m6, sức chứa 4–5 khách. View biển trực diện. Giá 500.000–600.000đ/đêm (cuối tuần/cao điểm cao hơn).",
        max_occupancy=5,
        base_price_per_night=Decimal("500000"),
        amenities=AMENITIES,
    ),
    RoomCreate(
        room_number="102",
        room_type="double",
        name="Phòng Đôi View Biển 2",
        description="Phòng đôi 2 giường 1m6, sức chứa 4–5 khách. View biển trực diện. Giá 500.000–600.000đ/đêm (cuối tuần/cao điểm cao hơn).",
        max_occupancy=5,
        base_price_per_night=Decimal("500000"),
        amenities=AMENITIES,
    ),
    RoomCreate(
        room_number="103",
        room_type="double",
        name="Phòng Đôi View Biển 3",
        description="Phòng đôi 2 giường 1m6, sức chứa 4–5 khách. View biển trực diện. Giá 500.000–600.000đ/đêm (cuối tuần/cao điểm cao hơn).",
        max_occupancy=5,
        base_price_per_night=Decimal("500000"),
        amenities=AMENITIES,
    ),
    RoomCreate(
        room_number="104",
        room_type="single",
        name="Phòng Đơn View Biển",
        description="Phòng đơn 1 giường 1m6, sức chứa 2 khách. Giá 300.000–400.000đ/đêm (cuối tuần/cao điểm cao hơn).",
        max_occupancy=2,
        base_price_per_night=Decimal("300000"),
        amenities=AMENITIES,
    ),
    RoomCreate(
        room_number="105",
        room_type="triple",
        name="Phòng 3 Khách View Biển",
        description="Phòng 1 giường 2m, sức chứa 3 khách. View biển trực diện. Giá 400.000đ/đêm.",
        max_occupancy=3,
        base_price_per_night=Decimal("400000"),
        amenities=AMENITIES,
    ),
]


async def seed() -> None:
    async with SessionLocal() as session:
        # --- Purge sample data (FK order: availability -> bookings -> rooms) ---
        # room_availability references both bookings and rooms, so it goes first.
        print("Purging sample data...")
        for model in (RoomAvailability, Booking, Room):
            res = await session.execute(delete(model))
            print(f"  - deleted {res.rowcount} {model.__tablename__}")
        await session.commit()

        # --- Insert real rooms (create_room regenerates availability) ---
        print("\nSeeding real View Biển rooms...")
        room_svc = RoomService(session)
        for r in ROOMS:
            await room_svc.create_room(r)
            print(f"  + Room {r.room_number}: {r.name} "
                  f"({r.base_price_per_night:,.0f}đ/đêm from, max {r.max_occupancy})")
        await session.commit()
        print("\nDone. 5 real rooms seeded, sample bookings/rooms removed.")


if __name__ == "__main__":
    asyncio.run(seed())
