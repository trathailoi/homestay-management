#!/usr/bin/env python3
"""Seed the database with sample data for development and testing.

Run:
  docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app python scripts/seed_data.py'

Creates:
- 1 admin user + 1 receptionist user
- 6 rooms (various types and price points)
- 10 bookings in various statuses (pending, confirmed, checked_in, checked_out, cancelled)

The script is idempotent - it checks for existing data before inserting.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select, update

from app.database import SessionLocal
from app.exceptions import HomestayError
from app.models import Booking, Room, RoomAvailability
from app.schemas.booking import BookingCreate
from app.schemas.room import RoomCreate
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.room_service import RoomService


USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "receptionist", "password": "reception123", "role": "receptionist"},
]

ROOMS = [
    RoomCreate(
        room_number="101",
        room_type="standard",
        name="Garden View Room",
        description="Cozy ground-floor room overlooking the garden. Perfect for solo travelers or couples.",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
        amenities=["WiFi", "Air Conditioning", "Garden View"],
    ),
    RoomCreate(
        room_number="102",
        room_type="standard",
        name="Courtyard Room",
        description="Quiet room facing the inner courtyard with natural light.",
        max_occupancy=2,
        base_price_per_night=Decimal("75.00"),
        amenities=["WiFi", "Air Conditioning", "Desk"],
    ),
    RoomCreate(
        room_number="201",
        room_type="deluxe",
        name="Mountain View Suite",
        description="Spacious suite on the second floor with panoramic mountain views and a private balcony.",
        max_occupancy=3,
        base_price_per_night=Decimal("120.00"),
        amenities=["WiFi", "Air Conditioning", "Balcony", "Mountain View", "Mini Fridge"],
    ),
    RoomCreate(
        room_number="202",
        room_type="deluxe",
        name="Sunset Room",
        description="West-facing deluxe room with stunning sunset views. Features a sitting area.",
        max_occupancy=3,
        base_price_per_night=Decimal("130.00"),
        amenities=["WiFi", "Air Conditioning", "Balcony", "Sunset View", "Sitting Area"],
    ),
    RoomCreate(
        room_number="301",
        room_type="family",
        name="Family Loft",
        description="Two-level family room with a loft sleeping area for children. Includes a small kitchenette.",
        max_occupancy=5,
        base_price_per_night=Decimal("180.00"),
        amenities=["WiFi", "Air Conditioning", "Kitchenette", "Loft", "Extra Beds"],
    ),
    RoomCreate(
        room_number="302",
        room_type="dormitory",
        name="Backpacker Dorm",
        description="Shared dormitory room with individual bunk beds, lockers, and a communal vibe.",
        max_occupancy=6,
        base_price_per_night=Decimal("25.00"),
        amenities=["WiFi", "Shared Bathroom", "Lockers", "Reading Light"],
    ),
]

today = date.today()

BOOKINGS = [
    # Currently checked in (past check-in dates require direct insert)
    {
        "room_number": "201",
        "guest_name": "Sarah Chen",
        "guest_phone": "+1-555-0101",
        "check_in_date": today - timedelta(days=2),
        "check_out_date": today + timedelta(days=3),
        "num_guests": 2,
        "special_requests": "Extra pillows please",
        "target_status": "checked_in",
    },
    {
        "room_number": "101",
        "guest_name": "Marco Rossi",
        "guest_phone": "+39-333-1234567",
        "check_in_date": today - timedelta(days=1),
        "check_out_date": today + timedelta(days=4),
        "num_guests": 1,
        "special_requests": None,
        "target_status": "checked_in",
    },
    # Confirmed upcoming
    {
        "room_number": "202",
        "guest_name": "Yuki Tanaka",
        "guest_phone": "+81-90-1234-5678",
        "check_in_date": today + timedelta(days=3),
        "check_out_date": today + timedelta(days=7),
        "num_guests": 2,
        "special_requests": "Late check-in around 10pm",
        "target_status": "confirmed",
    },
    {
        "room_number": "301",
        "guest_name": "The Johnson Family",
        "guest_phone": "+1-555-0202",
        "check_in_date": today + timedelta(days=5),
        "check_out_date": today + timedelta(days=12),
        "num_guests": 4,
        "special_requests": "Two children aged 5 and 8. Need a crib if possible.",
        "target_status": "confirmed",
    },
    # Pending (awaiting confirmation)
    {
        "room_number": "102",
        "guest_name": "Anna Mueller",
        "guest_phone": "+49-170-9876543",
        "check_in_date": today + timedelta(days=7),
        "check_out_date": today + timedelta(days=10),
        "num_guests": 2,
        "special_requests": "Vegetarian breakfast options",
        "target_status": "pending",
    },
    {
        "room_number": "302",
        "guest_name": "James Backpacker",
        "guest_phone": "+61-400-123456",
        "check_in_date": today + timedelta(days=2),
        "check_out_date": today + timedelta(days=8),
        "num_guests": 1,
        "special_requests": None,
        "target_status": "pending",
    },
    {
        "room_number": "201",
        "guest_name": "Priya Sharma",
        "guest_phone": "+91-98765-43210",
        "check_in_date": today + timedelta(days=10),
        "check_out_date": today + timedelta(days=14),
        "num_guests": 3,
        "special_requests": "Anniversary celebration - any special arrangement appreciated",
        "target_status": "pending",
    },
    # Checked out (past dates)
    {
        "room_number": "102",
        "guest_name": "Tom Wilson",
        "guest_phone": "+1-555-0303",
        "check_in_date": today - timedelta(days=7),
        "check_out_date": today - timedelta(days=3),
        "num_guests": 1,
        "special_requests": None,
        "target_status": "checked_out",
    },
    # Cancelled (use room 102 which has no date conflict)
    {
        "room_number": "102",
        "guest_name": "Lisa Park",
        "guest_phone": "+82-10-9876-5432",
        "check_in_date": today + timedelta(days=1),
        "check_out_date": today + timedelta(days=4),
        "num_guests": 2,
        "special_requests": "Airport pickup needed",
        "target_status": "cancelled",
        "cancel_reason": "Flight cancelled due to weather",
    },
    {
        "room_number": "301",
        "guest_name": "David Brown",
        "guest_phone": "+44-7700-900123",
        "check_in_date": today + timedelta(days=14),
        "check_out_date": today + timedelta(days=18),
        "num_guests": 5,
        "special_requests": None,
        "target_status": "cancelled",
        "cancel_reason": "Changed travel plans",
    },
]


async def _insert_direct_booking(session, room, b):
    """Insert a booking directly, bypassing service validation.

    Used for bookings with past check-in dates (checked_in, checked_out)
    where the service would reject the date.
    Also marks availability rows as unavailable.
    """
    num_nights = (b["check_out_date"] - b["check_in_date"]).days
    total = Decimal(str(room.base_price_per_night)) * num_nights

    booking = Booking(
        room_id=room.id,
        guest_name=b["guest_name"],
        guest_phone=b["guest_phone"],
        check_in_date=b["check_in_date"],
        check_out_date=b["check_out_date"],
        num_guests=b["num_guests"],
        total_amount=total,
        status=b["target_status"],
        special_requests=b["special_requests"],
        idempotency_key=f"seed-{b['guest_name'].lower().replace(' ', '-')}",
    )
    session.add(booking)
    await session.flush()

    # Mark availability rows as unavailable for future dates in the range
    dates_in_range = [
        b["check_in_date"] + timedelta(days=i) for i in range(num_nights)
    ]
    # Only update rows that exist (availability is generated from today onward)
    future_dates = [d for d in dates_in_range if d >= today]
    if future_dates:
        await session.execute(
            update(RoomAvailability)
            .where(
                and_(
                    RoomAvailability.room_id == room.id,
                    RoomAvailability.date.in_(future_dates),
                )
            )
            .values(is_available=False, booking_id=booking.id)
        )

    await session.commit()
    return booking


async def seed() -> None:
    async with SessionLocal() as session:
        # --- Users ---
        print("Seeding users...")
        auth = AuthService(session)
        for u in USERS:
            try:
                await auth.register(**u)
                print(f"  + Created {u['role']}: {u['username']} (password: {u['password']})")
            except HomestayError as e:
                if e.code == "USERNAME_EXISTS":
                    print(f"  - {u['username']} already exists, skipping")
                else:
                    raise

        # --- Rooms ---
        print("\nSeeding rooms...")
        room_svc = RoomService(session)

        count = await session.scalar(select(func.count()).select_from(Room))
        if count and count > 0:
            print(f"  - {count} rooms already exist, skipping room creation")
        else:
            for r in ROOMS:
                await room_svc.create_room(r)
                print(f"  + Room {r.room_number}: {r.name} (${r.base_price_per_night}/night, max {r.max_occupancy} guests)")

        # Build room_number -> room lookup
        result = await session.execute(select(Room))
        rooms = {r.room_number: r for r in result.scalars().all()}

        # --- Bookings ---
        print("\nSeeding bookings...")
        booking_svc = BookingService(session)

        # Check if bookings already exist
        booking_count = await session.scalar(select(func.count()).select_from(Booking))
        if booking_count and booking_count > 0:
            print(f"  - {booking_count} bookings already exist, skipping booking creation")
        else:
            for b in BOOKINGS:
                room = rooms.get(b["room_number"])
                if not room:
                    print(f"  ! Room {b['room_number']} not found, skipping {b['guest_name']}")
                    continue

                target = b["target_status"]
                needs_direct_insert = target in ("checked_in", "checked_out")

                if needs_direct_insert:
                    booking = await _insert_direct_booking(session, room, b)
                else:
                    try:
                        create_data = BookingCreate(
                            room_id=room.id,
                            guest_name=b["guest_name"],
                            guest_phone=b["guest_phone"],
                            check_in_date=b["check_in_date"],
                            check_out_date=b["check_out_date"],
                            num_guests=b["num_guests"],
                            special_requests=b["special_requests"],
                            idempotency_key=f"seed-{b['guest_name'].lower().replace(' ', '-')}",
                        )
                        booking = await booking_svc.create_booking(create_data)
                    except Exception as e:
                        print(f"  ! Failed to create booking for {b['guest_name']}: {e}")
                        continue

                    # Transition to target status via the service
                    try:
                        if target == "confirmed":
                            await booking_svc.confirm_booking(booking.id)
                        elif target == "cancelled":
                            await booking_svc.cancel_booking(booking.id, b.get("cancel_reason"))
                    except Exception as e:
                        print(f"  ! Failed to transition {b['guest_name']} to {target}: {e}")
                        continue

                icon = {"pending": "?", "confirmed": "+", "checked_in": ">", "checked_out": "<", "cancelled": "x"}
                print(
                    f"  {icon.get(target, ' ')} [{target:12s}] {b['guest_name']:25s} "
                    f"Room {b['room_number']} | {b['check_in_date']} to {b['check_out_date']} "
                    f"({b['num_guests']} guest{'s' if b['num_guests'] > 1 else ''})"
                )

        print("\nSeeding complete!")
        print("\nLogin credentials:")
        for u in USERS:
            print(f"  {u['role']:15s} -> {u['username']} / {u['password']}")


if __name__ == "__main__":
    asyncio.run(seed())
