# Homestay Management System - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a homestay management API with rooms, availability, and bookings -- exposed as both REST (FastAPI) and MCP server.

**Architecture:** Layered design -- FastAPI routes and MCP tools both call a shared service layer, which uses SQLAlchemy async ORM to talk to PostgreSQL. Alembic handles migrations.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy (async), PostgreSQL 18, Alembic, FastMCP 3.x, uv (package manager), pytest + httpx (testing)

---

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Initialize the project with uv**

```bash
cd /tmp/homestay-management
uv init --no-readme
```

Then replace the generated `pyproject.toml` with:

```toml
[project]
name = "homestay-management"
version = "0.1.0"
description = "Homestay management API with REST and MCP interfaces"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.0.0",
    "fastmcp>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
    "aiosqlite>=0.21.0",
]
```

**Step 2: Install dependencies**

```bash
uv sync --all-extras
```

Expected: Dependencies install successfully, `.venv/` created.

**Step 3: Create config module**

Create `app/__init__.py` (empty file).

Create `app/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/homestay"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/homestay"
    availability_window_days: int = 365

    model_config = {"env_prefix": "HOMESTAY_", "env_file": ".env"}


settings = Settings()
```

Create `tests/__init__.py` (empty file).

Create `tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(session):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
```

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock app/__init__.py app/config.py tests/__init__.py tests/conftest.py .python-version
git commit -m "feat: project scaffolding with FastAPI, SQLAlchemy, and test setup"
```

---

### Task 2: Database setup and SQLAlchemy models

**Files:**
- Create: `app/database.py`
- Create: `app/models/__init__.py`
- Create: `app/models/room.py`
- Create: `app/models/booking.py`
- Create: `app/models/room_availability.py`

**Step 1: Create the PostgreSQL database**

```bash
sudo -u postgres createdb homestay
```

**Step 2: Create database module**

Create `app/database.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

**Step 3: Create Room model**

Create `app/models/__init__.py`:

```python
from app.models.room import Room
from app.models.booking import Booking
from app.models.room_availability import RoomAvailability

__all__ = ["Room", "Booking", "RoomAvailability"]
```

Create `app/models/room.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Numeric, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    room_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_occupancy: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price_per_night: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amenities: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    availability = relationship("RoomAvailability", back_populates="room", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="room")
```

**Step 4: Create Booking model**

Create `app/models/booking.py`:

```python
import uuid
from datetime import date, datetime

from sqlalchemy import String, Integer, Numeric, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guest_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    num_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    room = relationship("Room", back_populates="bookings")
    availability_dates = relationship("RoomAvailability", back_populates="booking")
```

**Step 5: Create RoomAvailability model**

Create `app/models/room_availability.py`:

```python
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoomAvailability(Base):
    __tablename__ = "room_availability"
    __table_args__ = (UniqueConstraint("room_id", "date", name="uq_room_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)

    room = relationship("Room", back_populates="availability")
    booking = relationship("Booking", back_populates="availability_dates")
```

**Step 6: Write test to verify models load correctly**

Create `tests/test_models.py`:

```python
import pytest
from app.models import Room, Booking, RoomAvailability


def test_room_model_exists():
    assert Room.__tablename__ == "rooms"


def test_booking_model_exists():
    assert Booking.__tablename__ == "bookings"


def test_room_availability_model_exists():
    assert RoomAvailability.__tablename__ == "room_availability"
```

**Step 7: Run tests**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 3 tests PASS.

**Step 8: Commit**

```bash
git add app/database.py app/models/
git commit -m "feat: add SQLAlchemy models for rooms, bookings, and room_availability"
```

---

### Task 3: Alembic migrations setup

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/` (auto-generated)

**Step 1: Initialize Alembic**

```bash
uv run alembic init alembic
```

**Step 2: Edit `alembic/env.py`**

Replace the `target_metadata` and `run_migrations_online` sections to use async and import our models:

```python
# Near the top, after existing imports:
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.database import Base
from app.models import Room, Booking, RoomAvailability  # noqa: F401 - ensure models registered

target_metadata = Base.metadata

# Replace run_migrations_online with async version
```

The key changes:
1. Set `target_metadata = Base.metadata`
2. Set `sqlalchemy.url` from `settings.database_url` (the asyncpg URL)
3. Use async engine for online migrations

**Step 3: Update `alembic.ini`**

Set `sqlalchemy.url` to empty (we'll set it from env.py):

```ini
sqlalchemy.url =
```

**Step 4: Generate initial migration**

```bash
uv run alembic revision --autogenerate -m "create rooms bookings and room_availability tables"
```

Expected: A migration file is created in `alembic/versions/`.

**Step 5: Run migration**

```bash
uv run alembic upgrade head
```

Expected: Tables created in the `homestay` database.

**Step 6: Verify tables exist**

```bash
sudo -u postgres psql -d homestay -c "\dt"
```

Expected: Shows `rooms`, `bookings`, `room_availability`, and `alembic_version` tables.

**Step 7: Commit**

```bash
git add alembic.ini alembic/ tests/test_models.py
git commit -m "feat: add Alembic migrations for initial schema"
```

---

### Task 4: Pydantic schemas and response envelope

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/common.py`
- Create: `app/schemas/room.py`
- Create: `app/schemas/booking.py`
- Create: `app/schemas/availability.py`

**Step 1: Create response envelope schemas**

Create `app/schemas/__init__.py` (empty file).

Create `app/schemas/common.py`:

```python
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    total: int = 0
    page: int = 1
    per_page: int = 20


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Meta | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class ListResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: Meta
```

**Step 2: Create room schemas**

Create `app/schemas/room.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    room_number: str = Field(..., max_length=20, examples=["101"])
    room_type: str = Field(..., max_length=50, examples=["standard"])
    name: str = Field(..., max_length=100, examples=["Garden View Room"])
    description: str | None = None
    max_occupancy: int = Field(..., gt=0, examples=[2])
    base_price_per_night: float = Field(..., gt=0, examples=[75.00])
    amenities: list[str] | None = Field(default=None, examples=[["wifi", "ac"]])


class RoomUpdate(BaseModel):
    room_type: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    max_occupancy: int | None = Field(None, gt=0)
    base_price_per_night: float | None = Field(None, gt=0)
    amenities: list[str] | None = None
    status: str | None = Field(None, pattern="^(active|maintenance|inactive)$")


class RoomResponse(BaseModel):
    id: uuid.UUID
    room_number: str
    room_type: str
    name: str
    description: str | None
    max_occupancy: int
    base_price_per_night: float
    amenities: list[str] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 3: Create booking schemas**

Create `app/schemas/booking.py`:

```python
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    room_id: uuid.UUID
    guest_name: str = Field(..., max_length=200)
    guest_phone: str = Field(..., max_length=50)
    check_in_date: date
    check_out_date: date
    num_guests: int = Field(..., gt=0)
    special_requests: str | None = None
    idempotency_key: str | None = Field(None, max_length=100)


class BookingUpdate(BaseModel):
    guest_name: str | None = Field(None, max_length=200)
    guest_phone: str | None = Field(None, max_length=50)
    special_requests: str | None = None
    num_guests: int | None = Field(None, gt=0)


class BookingResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    guest_name: str
    guest_phone: str
    check_in_date: date
    check_out_date: date
    num_guests: int
    total_amount: float
    status: str
    special_requests: str | None
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 4: Create availability schemas**

Create `app/schemas/availability.py`:

```python
import uuid
from datetime import date

from pydantic import BaseModel, Field


class AvailabilityQuery(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(1, gt=0)


class RoomAvailabilityDay(BaseModel):
    date: date
    is_available: bool
    booking_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class AvailableRoom(BaseModel):
    id: uuid.UUID
    room_number: str
    room_type: str
    name: str
    max_occupancy: int
    base_price_per_night: float
    amenities: list[str] | None
    total_price: float  # calculated: nights * base_price_per_night

    model_config = {"from_attributes": True}
```

**Step 5: Write test for schemas**

Create `tests/test_schemas.py`:

```python
from datetime import date
from app.schemas.booking import BookingCreate
from app.schemas.room import RoomCreate


def test_room_create_schema():
    room = RoomCreate(
        room_number="101",
        room_type="standard",
        name="Garden View",
        max_occupancy=2,
        base_price_per_night=75.00,
    )
    assert room.room_number == "101"


def test_booking_create_schema():
    booking = BookingCreate(
        room_id="00000000-0000-0000-0000-000000000001",
        guest_name="John Doe",
        guest_phone="+84123456789",
        check_in_date=date(2026, 3, 15),
        check_out_date=date(2026, 3, 18),
        num_guests=2,
    )
    assert booking.num_guests == 2
```

**Step 6: Run tests**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: 2 tests PASS.

**Step 7: Commit**

```bash
git add app/schemas/ tests/test_schemas.py
git commit -m "feat: add Pydantic schemas for rooms, bookings, and availability"
```

---

### Task 5: Room service layer

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/room_service.py`
- Create: `tests/test_room_service.py`

**Step 1: Write failing tests for room service**

Create `app/services/__init__.py` (empty file).

Create `tests/test_room_service.py`:

```python
import pytest
from app.services.room_service import RoomService
from app.schemas.room import RoomCreate


@pytest.mark.asyncio
async def test_create_room(session):
    service = RoomService(session)
    room = await service.create_room(RoomCreate(
        room_number="101",
        room_type="standard",
        name="Garden View",
        max_occupancy=2,
        base_price_per_night=75.00,
        amenities=["wifi", "ac"],
    ))
    assert room.room_number == "101"
    assert room.status == "active"
    assert room.max_occupancy == 2


@pytest.mark.asyncio
async def test_list_rooms(session):
    service = RoomService(session)
    await service.create_room(RoomCreate(
        room_number="101", room_type="standard", name="Room 101",
        max_occupancy=2, base_price_per_night=75.00,
    ))
    await service.create_room(RoomCreate(
        room_number="102", room_type="deluxe", name="Room 102",
        max_occupancy=4, base_price_per_night=120.00,
    ))
    rooms, total = await service.list_rooms()
    assert total == 2


@pytest.mark.asyncio
async def test_get_room(session):
    service = RoomService(session)
    created = await service.create_room(RoomCreate(
        room_number="101", room_type="standard", name="Room 101",
        max_occupancy=2, base_price_per_night=75.00,
    ))
    room = await service.get_room(created.id)
    assert room is not None
    assert room.room_number == "101"


@pytest.mark.asyncio
async def test_get_room_not_found(session):
    service = RoomService(session)
    import uuid
    room = await service.get_room(uuid.uuid4())
    assert room is None


@pytest.mark.asyncio
async def test_update_room(session):
    service = RoomService(session)
    created = await service.create_room(RoomCreate(
        room_number="101", room_type="standard", name="Room 101",
        max_occupancy=2, base_price_per_night=75.00,
    ))
    from app.schemas.room import RoomUpdate
    updated = await service.update_room(created.id, RoomUpdate(name="Updated Room"))
    assert updated.name == "Updated Room"


@pytest.mark.asyncio
async def test_delete_room_sets_inactive(session):
    service = RoomService(session)
    created = await service.create_room(RoomCreate(
        room_number="101", room_type="standard", name="Room 101",
        max_occupancy=2, base_price_per_night=75.00,
    ))
    deleted = await service.delete_room(created.id)
    assert deleted.status == "inactive"


@pytest.mark.asyncio
async def test_create_room_generates_availability(session):
    service = RoomService(session)
    room = await service.create_room(RoomCreate(
        room_number="101", room_type="standard", name="Room 101",
        max_occupancy=2, base_price_per_night=75.00,
    ))
    from sqlalchemy import select, func
    from app.models.room_availability import RoomAvailability
    result = await session.execute(
        select(func.count()).where(RoomAvailability.room_id == room.id)
    )
    count = result.scalar()
    assert count == 365
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_room_service.py -v
```

Expected: FAIL (module not found).

**Step 3: Implement room service**

Create `app/services/room_service.py`:

```python
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.room import Room
from app.models.room_availability import RoomAvailability
from app.schemas.room import RoomCreate, RoomUpdate


class RoomService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_room(self, data: RoomCreate) -> Room:
        room = Room(
            room_number=data.room_number,
            room_type=data.room_type,
            name=data.name,
            description=data.description,
            max_occupancy=data.max_occupancy,
            base_price_per_night=data.base_price_per_night,
            amenities=data.amenities or [],
        )
        self.session.add(room)
        await self.session.flush()

        # Generate availability for the next N days
        today = date.today()
        availability_rows = [
            RoomAvailability(room_id=room.id, date=today + timedelta(days=i), is_available=True)
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
        query = select(Room)
        count_query = select(func.count()).select_from(Room)

        if room_type:
            query = query.where(Room.room_type == room_type)
            count_query = count_query.where(Room.room_type == room_type)
        if status:
            query = query.where(Room.status == status)
            count_query = count_query.where(Room.status == status)

        total = (await self.session.execute(count_query)).scalar() or 0
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_room(self, room_id: uuid.UUID) -> Room | None:
        return await self.session.get(Room, room_id)

    async def update_room(self, room_id: uuid.UUID, data: RoomUpdate) -> Room | None:
        room = await self.session.get(Room, room_id)
        if not room:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(room, key, value)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def delete_room(self, room_id: uuid.UUID) -> Room | None:
        room = await self.session.get(Room, room_id)
        if not room:
            return None
        room.status = "inactive"
        await self.session.commit()
        await self.session.refresh(room)
        return room
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_room_service.py -v
```

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add app/services/ tests/test_room_service.py
git commit -m "feat: add room service with CRUD and availability generation"
```

---

### Task 6: Availability service layer

**Files:**
- Create: `app/services/availability_service.py`
- Create: `tests/test_availability_service.py`

**Step 1: Write failing tests**

Create `tests/test_availability_service.py`:

```python
import pytest
from datetime import date, timedelta
from app.services.room_service import RoomService
from app.services.availability_service import AvailabilityService
from app.schemas.room import RoomCreate


async def _create_test_room(session, room_number="101", max_occupancy=2, price=75.00):
    service = RoomService(session)
    return await service.create_room(RoomCreate(
        room_number=room_number, room_type="standard", name=f"Room {room_number}",
        max_occupancy=max_occupancy, base_price_per_night=price,
    ))


@pytest.mark.asyncio
async def test_check_availability_returns_available_rooms(session):
    await _create_test_room(session, "101")
    await _create_test_room(session, "102")
    service = AvailabilityService(session)
    today = date.today()
    rooms = await service.check_availability(
        check_in=today + timedelta(days=1),
        check_out=today + timedelta(days=3),
        guests=2,
    )
    assert len(rooms) == 2


@pytest.mark.asyncio
async def test_check_availability_filters_by_occupancy(session):
    await _create_test_room(session, "101", max_occupancy=2)
    await _create_test_room(session, "102", max_occupancy=4)
    service = AvailabilityService(session)
    today = date.today()
    rooms = await service.check_availability(
        check_in=today + timedelta(days=1),
        check_out=today + timedelta(days=3),
        guests=3,
    )
    assert len(rooms) == 1
    assert rooms[0]["room_number"] == "102"


@pytest.mark.asyncio
async def test_get_room_availability_calendar(session):
    room = await _create_test_room(session, "101")
    service = AvailabilityService(session)
    today = date.today()
    calendar = await service.get_room_calendar(
        room_id=room.id,
        start_date=today,
        end_date=today + timedelta(days=7),
    )
    assert len(calendar) == 7
    assert all(day.is_available for day in calendar)
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_availability_service.py -v
```

Expected: FAIL.

**Step 3: Implement availability service**

Create `app/services/availability_service.py`:

```python
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.room_availability import RoomAvailability


class AvailabilityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_availability(
        self, check_in: date, check_out: date, guests: int = 1
    ) -> list[dict]:
        num_nights = (check_out - check_in).days
        if num_nights <= 0:
            return []

        dates_needed = [check_in + timedelta(days=i) for i in range(num_nights)]

        # Find rooms where ALL requested dates are available and capacity is sufficient
        subquery = (
            select(RoomAvailability.room_id)
            .where(
                RoomAvailability.date.in_(dates_needed),
                RoomAvailability.is_available == True,  # noqa: E712
            )
            .group_by(RoomAvailability.room_id)
            .having(func.count(RoomAvailability.id) == num_nights)
            .subquery()
        )

        query = select(Room).where(
            Room.id.in_(select(subquery.c.room_id)),
            Room.max_occupancy >= guests,
            Room.status == "active",
        )
        result = await self.session.execute(query)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "room_number": room.room_number,
                "room_type": room.room_type,
                "name": room.name,
                "max_occupancy": room.max_occupancy,
                "base_price_per_night": float(room.base_price_per_night),
                "amenities": room.amenities,
                "total_price": float(room.base_price_per_night) * num_nights,
            }
            for room in rooms
        ]

    async def get_room_calendar(
        self, room_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[RoomAvailability]:
        query = (
            select(RoomAvailability)
            .where(
                RoomAvailability.room_id == room_id,
                RoomAvailability.date >= start_date,
                RoomAvailability.date < end_date,
            )
            .order_by(RoomAvailability.date)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_availability_service.py -v
```

Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add app/services/availability_service.py tests/test_availability_service.py
git commit -m "feat: add availability service with date-range queries"
```

---

### Task 7: Booking service layer

**Files:**
- Create: `app/services/booking_service.py`
- Create: `tests/test_booking_service.py`

**Step 1: Write failing tests**

Create `tests/test_booking_service.py`:

```python
import uuid
import pytest
from datetime import date, timedelta
from app.services.room_service import RoomService
from app.services.booking_service import BookingService
from app.schemas.room import RoomCreate
from app.schemas.booking import BookingCreate


async def _create_test_room(session, room_number="101"):
    service = RoomService(session)
    return await service.create_room(RoomCreate(
        room_number=room_number, room_type="standard", name=f"Room {room_number}",
        max_occupancy=2, base_price_per_night=75.00,
    ))


def _booking_data(room_id, days_from_now=1, nights=3, **kwargs):
    today = date.today()
    defaults = dict(
        room_id=room_id,
        guest_name="John Doe",
        guest_phone="+84123456789",
        check_in_date=today + timedelta(days=days_from_now),
        check_out_date=today + timedelta(days=days_from_now + nights),
        num_guests=2,
    )
    defaults.update(kwargs)
    return BookingCreate(**defaults)


@pytest.mark.asyncio
async def test_create_booking(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    booking = await service.create_booking(_booking_data(room.id))
    assert booking.status == "pending"
    assert booking.guest_name == "John Doe"
    assert float(booking.total_amount) == 225.00  # 3 nights * 75


@pytest.mark.asyncio
async def test_create_booking_marks_dates_unavailable(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    today = date.today()
    await service.create_booking(_booking_data(room.id, days_from_now=1, nights=3))

    from app.services.availability_service import AvailabilityService
    avail = AvailabilityService(session)
    rooms = await avail.check_availability(
        check_in=today + timedelta(days=1),
        check_out=today + timedelta(days=4),
        guests=1,
    )
    assert len(rooms) == 0  # room is now booked


@pytest.mark.asyncio
async def test_create_booking_conflict(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    await service.create_booking(_booking_data(room.id, days_from_now=1, nights=3))
    with pytest.raises(ValueError, match="not available"):
        await service.create_booking(_booking_data(room.id, days_from_now=2, nights=2))


@pytest.mark.asyncio
async def test_idempotent_booking(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    data = _booking_data(room.id, idempotency_key="test-key-1")
    b1 = await service.create_booking(data)
    b2 = await service.create_booking(data)
    assert b1.id == b2.id


@pytest.mark.asyncio
async def test_cancel_booking_releases_dates(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    today = date.today()
    booking = await service.create_booking(_booking_data(room.id, days_from_now=1, nights=3))
    await service.cancel_booking(booking.id)

    from app.services.availability_service import AvailabilityService
    avail = AvailabilityService(session)
    rooms = await avail.check_availability(
        check_in=today + timedelta(days=1),
        check_out=today + timedelta(days=4),
        guests=1,
    )
    assert len(rooms) == 1  # room is available again


@pytest.mark.asyncio
async def test_confirm_booking(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    booking = await service.create_booking(_booking_data(room.id))
    confirmed = await service.confirm_booking(booking.id)
    assert confirmed.status == "confirmed"


@pytest.mark.asyncio
async def test_check_in_booking(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    booking = await service.create_booking(_booking_data(room.id))
    await service.confirm_booking(booking.id)
    checked_in = await service.check_in(booking.id)
    assert checked_in.status == "checked_in"


@pytest.mark.asyncio
async def test_check_out_booking(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    booking = await service.create_booking(_booking_data(room.id))
    await service.confirm_booking(booking.id)
    await service.check_in(booking.id)
    checked_out = await service.check_out(booking.id)
    assert checked_out.status == "checked_out"


@pytest.mark.asyncio
async def test_invalid_status_transition(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    booking = await service.create_booking(_booking_data(room.id))
    # Can't check in a pending booking (must confirm first)
    with pytest.raises(ValueError, match="Cannot transition"):
        await service.check_in(booking.id)


@pytest.mark.asyncio
async def test_list_bookings(session):
    room = await _create_test_room(session)
    service = BookingService(session)
    await service.create_booking(_booking_data(room.id, days_from_now=1, nights=2))
    await service.create_booking(_booking_data(room.id, days_from_now=5, nights=2))
    bookings, total = await service.list_bookings()
    assert total == 2
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_booking_service.py -v
```

Expected: FAIL.

**Step 3: Implement booking service**

Create `app/services/booking_service.py`:

```python
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_availability import RoomAvailability
from app.schemas.booking import BookingCreate, BookingUpdate

# Valid state transitions
VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["checked_in", "cancelled"],
    "checked_in": ["checked_out"],
    "checked_out": [],
    "cancelled": [],
}


class BookingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_booking(self, data: BookingCreate) -> Booking:
        # Idempotency check
        if data.idempotency_key:
            existing = await self.session.execute(
                select(Booking).where(Booking.idempotency_key == data.idempotency_key)
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        # Validate dates
        if data.check_out_date <= data.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")

        # Validate room exists and check capacity
        room = await self.session.get(Room, data.room_id)
        if not room:
            raise ValueError(f"Room {data.room_id} not found")
        if data.num_guests > room.max_occupancy:
            raise ValueError(
                f"Room {room.room_number} max occupancy is {room.max_occupancy}, "
                f"requested {data.num_guests}"
            )

        num_nights = (data.check_out_date - data.check_in_date).days
        dates_needed = [data.check_in_date + timedelta(days=i) for i in range(num_nights)]

        # Check and lock availability rows
        avail_result = await self.session.execute(
            select(RoomAvailability)
            .where(
                RoomAvailability.room_id == data.room_id,
                RoomAvailability.date.in_(dates_needed),
                RoomAvailability.is_available == True,  # noqa: E712
            )
            .with_for_update()
        )
        available_rows = list(avail_result.scalars().all())

        if len(available_rows) != num_nights:
            raise ValueError(
                f"Room {room.room_number} is not available for all requested dates"
            )

        # Calculate total
        total_amount = float(room.base_price_per_night) * num_nights

        # Create booking
        booking = Booking(
            room_id=data.room_id,
            guest_name=data.guest_name,
            guest_phone=data.guest_phone,
            check_in_date=data.check_in_date,
            check_out_date=data.check_out_date,
            num_guests=data.num_guests,
            total_amount=total_amount,
            special_requests=data.special_requests,
            idempotency_key=data.idempotency_key,
        )
        self.session.add(booking)
        await self.session.flush()

        # Mark dates as unavailable
        for row in available_rows:
            row.is_available = False
            row.booking_id = booking.id

        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def get_booking(self, booking_id: uuid.UUID) -> Booking | None:
        return await self.session.get(Booking, booking_id)

    async def list_bookings(
        self,
        status: str | None = None,
        room_id: uuid.UUID | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Booking], int]:
        query = select(Booking)
        count_query = select(func.count()).select_from(Booking)

        if status:
            query = query.where(Booking.status == status)
            count_query = count_query.where(Booking.status == status)
        if room_id:
            query = query.where(Booking.room_id == room_id)
            count_query = count_query.where(Booking.room_id == room_id)

        total = (await self.session.execute(count_query)).scalar() or 0
        query = query.order_by(Booking.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_booking(self, booking_id: uuid.UUID, data: BookingUpdate) -> Booking | None:
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            return None
        if booking.status in ("cancelled", "checked_out"):
            raise ValueError(f"Cannot modify a {booking.status} booking")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(booking, key, value)
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def _transition(self, booking_id: uuid.UUID, new_status: str) -> Booking:
        booking = await self.session.get(Booking, booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        if new_status not in VALID_TRANSITIONS.get(booking.status, []):
            raise ValueError(
                f"Cannot transition from '{booking.status}' to '{new_status}'"
            )
        booking.status = new_status
        await self.session.commit()
        await self.session.refresh(booking)
        return booking

    async def confirm_booking(self, booking_id: uuid.UUID) -> Booking:
        return await self._transition(booking_id, "confirmed")

    async def cancel_booking(self, booking_id: uuid.UUID) -> Booking:
        booking = await self._transition(booking_id, "cancelled")
        # Release availability
        await self.session.execute(
            update(RoomAvailability)
            .where(RoomAvailability.booking_id == booking_id)
            .values(is_available=True, booking_id=None)
        )
        await self.session.commit()
        return booking

    async def check_in(self, booking_id: uuid.UUID) -> Booking:
        return await self._transition(booking_id, "checked_in")

    async def check_out(self, booking_id: uuid.UUID) -> Booking:
        return await self._transition(booking_id, "checked_out")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_booking_service.py -v
```

Expected: All 10 tests PASS.

**Step 5: Commit**

```bash
git add app/services/booking_service.py tests/test_booking_service.py
git commit -m "feat: add booking service with lifecycle management and conflict prevention"
```

---

### Task 8: FastAPI app entry point and health endpoint

**Files:**
- Create: `app/main.py`
- Create: `tests/test_health.py`

**Step 1: Write failing test**

Create `tests/test_health.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_health.py -v
```

Expected: FAIL.

**Step 3: Create FastAPI app**

Create `app/main.py`:

```python
from fastapi import FastAPI

from app.api.rooms import router as rooms_router
from app.api.bookings import router as bookings_router
from app.api.availability import router as availability_router

app = FastAPI(
    title="Homestay Management API",
    description="API for managing homestay rooms, availability, and bookings. Designed for AI agent interaction.",
    version="0.1.0",
)

app.include_router(rooms_router, prefix="/api/v1", tags=["rooms"])
app.include_router(bookings_router, prefix="/api/v1", tags=["bookings"])
app.include_router(availability_router, prefix="/api/v1", tags=["availability"])


@app.get("/api/v1/health")
async def health_check():
    return {"success": True, "data": {"status": "healthy"}}
```

Also create placeholder route files so the import works:

Create `app/api/__init__.py` (empty file).

Create `app/api/rooms.py`:

```python
from fastapi import APIRouter

router = APIRouter()
```

Create `app/api/bookings.py`:

```python
from fastapi import APIRouter

router = APIRouter()
```

Create `app/api/availability.py`:

```python
from fastapi import APIRouter

router = APIRouter()
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_health.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/main.py app/api/
git commit -m "feat: add FastAPI app with health endpoint and route placeholders"
```

---

### Task 9: Rooms API endpoints

**Files:**
- Modify: `app/api/rooms.py`
- Create: `tests/test_api_rooms.py`

**Step 1: Write failing tests**

Create `tests/test_api_rooms.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_room(client):
    response = await client.post("/api/v1/rooms", json={
        "room_number": "101",
        "room_type": "standard",
        "name": "Garden View",
        "max_occupancy": 2,
        "base_price_per_night": 75.00,
        "amenities": ["wifi", "ac"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["room_number"] == "101"


@pytest.mark.asyncio
async def test_list_rooms(client):
    await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    response = await client.get("/api/v1/rooms")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1


@pytest.mark.asyncio
async def test_get_room(client):
    create = await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    room_id = create.json()["data"]["id"]
    response = await client.get(f"/api/v1/rooms/{room_id}")
    assert response.status_code == 200
    assert response.json()["data"]["room_number"] == "101"


@pytest.mark.asyncio
async def test_get_room_not_found(client):
    response = await client.get("/api/v1/rooms/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "ROOM_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_room(client):
    create = await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    room_id = create.json()["data"]["id"]
    response = await client.put(f"/api/v1/rooms/{room_id}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_room(client):
    create = await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    room_id = create.json()["data"]["id"]
    response = await client.delete(f"/api/v1/rooms/{room_id}")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "inactive"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_api_rooms.py -v
```

Expected: FAIL (no route handlers).

**Step 3: Implement rooms API**

Replace `app/api/rooms.py`:

```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.common import SuccessResponse, ListResponse, ErrorResponse, ErrorDetail, Meta
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse
from app.services.room_service import RoomService

router = APIRouter()


@router.post("/rooms", response_model=SuccessResponse[RoomResponse], status_code=201)
async def create_room(data: RoomCreate, session: AsyncSession = Depends(get_session)):
    service = RoomService(session)
    room = await service.create_room(data)
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.get("/rooms", response_model=ListResponse[RoomResponse])
async def list_rooms(
    room_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    service = RoomService(session)
    rooms, total = await service.list_rooms(room_type=room_type, status=status, page=page, per_page=per_page)
    return ListResponse(
        data=[RoomResponse.model_validate(r) for r in rooms],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.get("/rooms/{room_id}", response_model=SuccessResponse[RoomResponse], responses={404: {"model": ErrorResponse}})
async def get_room(room_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = RoomService(session)
    room = await service.get_room(room_id)
    if not room:
        return ErrorResponse(error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room {room_id} not found"))
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.put("/rooms/{room_id}", response_model=SuccessResponse[RoomResponse], responses={404: {"model": ErrorResponse}})
async def update_room(room_id: uuid.UUID, data: RoomUpdate, session: AsyncSession = Depends(get_session)):
    service = RoomService(session)
    room = await service.update_room(room_id, data)
    if not room:
        return ErrorResponse(error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room {room_id} not found"))
    return SuccessResponse(data=RoomResponse.model_validate(room))


@router.delete("/rooms/{room_id}", response_model=SuccessResponse[RoomResponse], responses={404: {"model": ErrorResponse}})
async def delete_room(room_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = RoomService(session)
    room = await service.delete_room(room_id)
    if not room:
        return ErrorResponse(error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room {room_id} not found"))
    return SuccessResponse(data=RoomResponse.model_validate(room))
```

Note: The `get_room`, `update_room`, and `delete_room` endpoints need to return proper 404 HTTP status codes. Use `JSONResponse` for error returns:

Update the error returns to use `JSONResponse`:

```python
from fastapi.responses import JSONResponse

# In the not-found cases, return:
return JSONResponse(
    status_code=404,
    content=ErrorResponse(error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room {room_id} not found")).model_dump(),
)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api_rooms.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add app/api/rooms.py tests/test_api_rooms.py
git commit -m "feat: add rooms REST API endpoints with CRUD operations"
```

---

### Task 10: Availability API endpoints

**Files:**
- Modify: `app/api/availability.py`
- Create: `tests/test_api_availability.py`

**Step 1: Write failing tests**

Create `tests/test_api_availability.py`:

```python
import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_check_availability(client):
    await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    today = date.today()
    check_in = (today + timedelta(days=1)).isoformat()
    check_out = (today + timedelta(days=4)).isoformat()
    response = await client.get(f"/api/v1/availability?check_in={check_in}&check_out={check_out}&guests=2")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["total_price"] == 225.00


@pytest.mark.asyncio
async def test_room_availability_calendar(client):
    create = await client.post("/api/v1/rooms", json={
        "room_number": "101", "room_type": "standard", "name": "Room 101",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    room_id = create.json()["data"]["id"]
    today = date.today()
    start = today.isoformat()
    end = (today + timedelta(days=7)).isoformat()
    response = await client.get(f"/api/v1/rooms/{room_id}/availability?start_date={start}&end_date={end}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 7
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_api_availability.py -v
```

Expected: FAIL.

**Step 3: Implement availability API**

Replace `app/api/availability.py`:

```python
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.availability import AvailableRoom, RoomAvailabilityDay
from app.schemas.common import ListResponse, SuccessResponse, Meta
from app.services.availability_service import AvailabilityService

router = APIRouter()


@router.get("/availability", response_model=ListResponse[AvailableRoom])
async def check_availability(
    check_in: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    check_out: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    guests: int = Query(1, ge=1, description="Number of guests"),
    session: AsyncSession = Depends(get_session),
):
    service = AvailabilityService(session)
    rooms = await service.check_availability(check_in, check_out, guests)
    return ListResponse(
        data=[AvailableRoom(**r) for r in rooms],
        meta=Meta(total=len(rooms)),
    )


@router.get("/rooms/{room_id}/availability", response_model=SuccessResponse[list[RoomAvailabilityDay]])
async def get_room_calendar(
    room_id: uuid.UUID,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
):
    service = AvailabilityService(session)
    calendar = await service.get_room_calendar(room_id, start_date, end_date)
    return SuccessResponse(data=[RoomAvailabilityDay.model_validate(day) for day in calendar])
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api_availability.py -v
```

Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
git add app/api/availability.py tests/test_api_availability.py
git commit -m "feat: add availability API endpoints"
```

---

### Task 11: Bookings API endpoints

**Files:**
- Modify: `app/api/bookings.py`
- Create: `tests/test_api_bookings.py`

**Step 1: Write failing tests**

Create `tests/test_api_bookings.py`:

```python
import pytest
from datetime import date, timedelta


async def _create_room(client, room_number="101"):
    resp = await client.post("/api/v1/rooms", json={
        "room_number": room_number, "room_type": "standard", "name": f"Room {room_number}",
        "max_occupancy": 2, "base_price_per_night": 75.00,
    })
    return resp.json()["data"]["id"]


def _booking_json(room_id, days_from_now=1, nights=3):
    today = date.today()
    return {
        "room_id": room_id,
        "guest_name": "John Doe",
        "guest_phone": "+84123456789",
        "check_in_date": (today + timedelta(days=days_from_now)).isoformat(),
        "check_out_date": (today + timedelta(days=days_from_now + nights)).isoformat(),
        "num_guests": 2,
    }


@pytest.mark.asyncio
async def test_create_booking(client):
    room_id = await _create_room(client)
    response = await client.post("/api/v1/bookings", json=_booking_json(room_id))
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "pending"
    assert data["data"]["total_amount"] == 225.00


@pytest.mark.asyncio
async def test_create_booking_conflict(client):
    room_id = await _create_room(client)
    await client.post("/api/v1/bookings", json=_booking_json(room_id))
    response = await client.post("/api/v1/bookings", json=_booking_json(room_id, days_from_now=2, nights=2))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROOM_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_get_booking(client):
    room_id = await _create_room(client)
    create = await client.post("/api/v1/bookings", json=_booking_json(room_id))
    booking_id = create.json()["data"]["id"]
    response = await client.get(f"/api/v1/bookings/{booking_id}")
    assert response.status_code == 200
    assert response.json()["data"]["guest_name"] == "John Doe"


@pytest.mark.asyncio
async def test_list_bookings(client):
    room_id = await _create_room(client)
    await client.post("/api/v1/bookings", json=_booking_json(room_id, days_from_now=1, nights=2))
    await client.post("/api/v1/bookings", json=_booking_json(room_id, days_from_now=5, nights=2))
    response = await client.get("/api/v1/bookings")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_confirm_booking(client):
    room_id = await _create_room(client)
    create = await client.post("/api/v1/bookings", json=_booking_json(room_id))
    booking_id = create.json()["data"]["id"]
    response = await client.post(f"/api/v1/bookings/{booking_id}/confirm")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_cancel_booking(client):
    room_id = await _create_room(client)
    create = await client.post("/api/v1/bookings", json=_booking_json(room_id))
    booking_id = create.json()["data"]["id"]
    response = await client.post(f"/api/v1/bookings/{booking_id}/cancel")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_check_in_out_flow(client):
    room_id = await _create_room(client)
    create = await client.post("/api/v1/bookings", json=_booking_json(room_id))
    booking_id = create.json()["data"]["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/confirm")
    resp_in = await client.post(f"/api/v1/bookings/{booking_id}/check-in")
    assert resp_in.json()["data"]["status"] == "checked_in"
    resp_out = await client.post(f"/api/v1/bookings/{booking_id}/check-out")
    assert resp_out.json()["data"]["status"] == "checked_out"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_api_bookings.py -v
```

Expected: FAIL.

**Step 3: Implement bookings API**

Replace `app/api/bookings.py`:

```python
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse
from app.schemas.common import SuccessResponse, ListResponse, ErrorResponse, ErrorDetail, Meta
from app.services.booking_service import BookingService

router = APIRouter()


@router.post("/bookings", response_model=SuccessResponse[BookingResponse], status_code=201)
async def create_booking(data: BookingCreate, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.create_booking(data)
    except ValueError as e:
        error_msg = str(e)
        if "not available" in error_msg:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error=ErrorDetail(code="ROOM_NOT_AVAILABLE", message=error_msg)
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="VALIDATION_ERROR", message=error_msg)
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.get("/bookings", response_model=ListResponse[BookingResponse])
async def list_bookings(
    status: str | None = Query(None),
    room_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    service = BookingService(session)
    bookings, total = await service.list_bookings(status=status, room_id=room_id, page=page, per_page=per_page)
    return ListResponse(
        data=[BookingResponse.model_validate(b) for b in bookings],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.get("/bookings/{booking_id}", response_model=SuccessResponse[BookingResponse])
async def get_booking(booking_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    booking = await service.get_booking(booking_id)
    if not booking:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(code="BOOKING_NOT_FOUND", message=f"Booking {booking_id} not found")
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.put("/bookings/{booking_id}", response_model=SuccessResponse[BookingResponse])
async def update_booking(booking_id: uuid.UUID, data: BookingUpdate, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.update_booking(booking_id, data)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="INVALID_OPERATION", message=str(e))
            ).model_dump(),
        )
    if not booking:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(code="BOOKING_NOT_FOUND", message=f"Booking {booking_id} not found")
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.post("/bookings/{booking_id}/confirm", response_model=SuccessResponse[BookingResponse])
async def confirm_booking(booking_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.confirm_booking(booking_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="INVALID_STATUS_TRANSITION", message=str(e))
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.post("/bookings/{booking_id}/cancel", response_model=SuccessResponse[BookingResponse])
async def cancel_booking(booking_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.cancel_booking(booking_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="INVALID_STATUS_TRANSITION", message=str(e))
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.post("/bookings/{booking_id}/check-in", response_model=SuccessResponse[BookingResponse])
async def check_in(booking_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.check_in(booking_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="INVALID_STATUS_TRANSITION", message=str(e))
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.post("/bookings/{booking_id}/check-out", response_model=SuccessResponse[BookingResponse])
async def check_out(booking_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    service = BookingService(session)
    try:
        booking = await service.check_out(booking_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="INVALID_STATUS_TRANSITION", message=str(e))
            ).model_dump(),
        )
    return SuccessResponse(data=BookingResponse.model_validate(booking))
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api_bookings.py -v
```

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add app/api/bookings.py tests/test_api_bookings.py
git commit -m "feat: add bookings REST API endpoints with full lifecycle"
```

---

### Task 12: MCP server

**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/server.py`
- Create: `tests/test_mcp_tools.py`

**Step 1: Write tests for MCP tools**

Create `tests/test_mcp_tools.py`:

```python
import pytest
from datetime import date, timedelta

from mcp_server.server import mcp


@pytest.mark.asyncio
async def test_mcp_list_tools():
    """Verify all expected tools are registered."""
    # FastMCP exposes tools - check they exist
    tools = await mcp.get_tools()
    tool_names = [t.name for t in tools]
    assert "list_rooms" in tool_names
    assert "check_availability" in tool_names
    assert "create_booking" in tool_names
    assert "cancel_booking" in tool_names
```

**Step 2: Create MCP server**

Create `mcp_server/__init__.py` (empty file).

Create `mcp_server/server.py`:

```python
import uuid
from datetime import date

from fastmcp import FastMCP

from app.database import SessionLocal
from app.services.room_service import RoomService
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.schemas.room import RoomCreate, RoomUpdate
from app.schemas.booking import BookingCreate

mcp = FastMCP(
    "Homestay Management",
    instructions=(
        "Manage homestay rooms, check availability, and handle bookings. "
        "Use check_availability before create_booking to verify room availability. "
        "Bookings follow the lifecycle: pending -> confirmed -> checked_in -> checked_out. "
        "Bookings can be cancelled from pending or confirmed status."
    ),
)


async def _get_session():
    async with SessionLocal() as session:
        yield session


@mcp.tool()
async def list_rooms(
    room_type: str | None = None,
    status: str | None = None,
) -> dict:
    """List all rooms in the homestay. Optionally filter by room_type (e.g., 'standard', 'deluxe') or status ('active', 'maintenance', 'inactive')."""
    async for session in _get_session():
        service = RoomService(session)
        rooms, total = await service.list_rooms(room_type=room_type, status=status)
        return {
            "rooms": [
                {
                    "id": str(r.id),
                    "room_number": r.room_number,
                    "room_type": r.room_type,
                    "name": r.name,
                    "max_occupancy": r.max_occupancy,
                    "base_price_per_night": float(r.base_price_per_night),
                    "amenities": r.amenities,
                    "status": r.status,
                }
                for r in rooms
            ],
            "total": total,
        }


@mcp.tool()
async def get_room(room_id: str) -> dict:
    """Get details of a specific room by its ID (UUID)."""
    async for session in _get_session():
        service = RoomService(session)
        room = await service.get_room(uuid.UUID(room_id))
        if not room:
            return {"error": "ROOM_NOT_FOUND", "message": f"Room {room_id} not found"}
        return {
            "id": str(room.id),
            "room_number": room.room_number,
            "room_type": room.room_type,
            "name": room.name,
            "description": room.description,
            "max_occupancy": room.max_occupancy,
            "base_price_per_night": float(room.base_price_per_night),
            "amenities": room.amenities,
            "status": room.status,
        }


@mcp.tool()
async def check_availability(
    check_in: str,
    check_out: str,
    guests: int = 1,
) -> dict:
    """Check which rooms are available for the given date range. Dates must be in YYYY-MM-DD format. Returns available rooms with total price for the stay."""
    async for session in _get_session():
        service = AvailabilityService(session)
        rooms = await service.check_availability(
            check_in=date.fromisoformat(check_in),
            check_out=date.fromisoformat(check_out),
            guests=guests,
        )
        return {"available_rooms": rooms, "total": len(rooms)}


@mcp.tool()
async def create_booking(
    room_id: str,
    guest_name: str,
    guest_phone: str,
    check_in_date: str,
    check_out_date: str,
    num_guests: int,
    special_requests: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Create a new booking. Dates in YYYY-MM-DD format. Use check_availability first to verify the room is free. Returns the created booking with status 'pending'."""
    async for session in _get_session():
        service = BookingService(session)
        try:
            booking = await service.create_booking(BookingCreate(
                room_id=uuid.UUID(room_id),
                guest_name=guest_name,
                guest_phone=guest_phone,
                check_in_date=date.fromisoformat(check_in_date),
                check_out_date=date.fromisoformat(check_out_date),
                num_guests=num_guests,
                special_requests=special_requests,
                idempotency_key=idempotency_key,
            ))
        except ValueError as e:
            return {"error": "BOOKING_FAILED", "message": str(e)}
        return {
            "id": str(booking.id),
            "room_id": str(booking.room_id),
            "guest_name": booking.guest_name,
            "status": booking.status,
            "check_in_date": booking.check_in_date.isoformat(),
            "check_out_date": booking.check_out_date.isoformat(),
            "total_amount": float(booking.total_amount),
        }


@mcp.tool()
async def get_booking(booking_id: str) -> dict:
    """Get details of a specific booking by its ID (UUID)."""
    async for session in _get_session():
        service = BookingService(session)
        booking = await service.get_booking(uuid.UUID(booking_id))
        if not booking:
            return {"error": "BOOKING_NOT_FOUND", "message": f"Booking {booking_id} not found"}
        return {
            "id": str(booking.id),
            "room_id": str(booking.room_id),
            "guest_name": booking.guest_name,
            "guest_phone": booking.guest_phone,
            "check_in_date": booking.check_in_date.isoformat(),
            "check_out_date": booking.check_out_date.isoformat(),
            "num_guests": booking.num_guests,
            "total_amount": float(booking.total_amount),
            "status": booking.status,
            "special_requests": booking.special_requests,
        }


@mcp.tool()
async def list_bookings(
    status: str | None = None,
    room_id: str | None = None,
) -> dict:
    """List bookings. Optionally filter by status ('pending', 'confirmed', 'cancelled', 'checked_in', 'checked_out') or room_id."""
    async for session in _get_session():
        service = BookingService(session)
        bookings, total = await service.list_bookings(
            status=status,
            room_id=uuid.UUID(room_id) if room_id else None,
        )
        return {
            "bookings": [
                {
                    "id": str(b.id),
                    "room_id": str(b.room_id),
                    "guest_name": b.guest_name,
                    "check_in_date": b.check_in_date.isoformat(),
                    "check_out_date": b.check_out_date.isoformat(),
                    "status": b.status,
                    "total_amount": float(b.total_amount),
                }
                for b in bookings
            ],
            "total": total,
        }


@mcp.tool()
async def confirm_booking(booking_id: str) -> dict:
    """Confirm a pending booking. Only works for bookings with status 'pending'."""
    async for session in _get_session():
        service = BookingService(session)
        try:
            booking = await service.confirm_booking(uuid.UUID(booking_id))
        except ValueError as e:
            return {"error": "INVALID_TRANSITION", "message": str(e)}
        return {"id": str(booking.id), "status": booking.status}


@mcp.tool()
async def cancel_booking(booking_id: str) -> dict:
    """Cancel a booking. Only works for bookings with status 'pending' or 'confirmed'. Releases the room dates back to available."""
    async for session in _get_session():
        service = BookingService(session)
        try:
            booking = await service.cancel_booking(uuid.UUID(booking_id))
        except ValueError as e:
            return {"error": "INVALID_TRANSITION", "message": str(e)}
        return {"id": str(booking.id), "status": booking.status}


@mcp.tool()
async def check_in(booking_id: str) -> dict:
    """Check in a guest. Only works for bookings with status 'confirmed'."""
    async for session in _get_session():
        service = BookingService(session)
        try:
            booking = await service.check_in(uuid.UUID(booking_id))
        except ValueError as e:
            return {"error": "INVALID_TRANSITION", "message": str(e)}
        return {"id": str(booking.id), "status": booking.status}


@mcp.tool()
async def check_out(booking_id: str) -> dict:
    """Check out a guest. Only works for bookings with status 'checked_in'."""
    async for session in _get_session():
        service = BookingService(session)
        try:
            booking = await service.check_out(uuid.UUID(booking_id))
        except ValueError as e:
            return {"error": "INVALID_TRANSITION", "message": str(e)}
        return {"id": str(booking.id), "status": booking.status}


if __name__ == "__main__":
    mcp.run()
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_mcp_tools.py -v
```

Expected: PASS (tool registration verified).

**Step 4: Commit**

```bash
git add mcp_server/ tests/test_mcp_tools.py
git commit -m "feat: add MCP server with all homestay management tools"
```

---

### Task 13: Docker Compose for local PostgreSQL and final integration

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: homestay
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Step 2: Create .env.example**

```
HOMESTAY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/homestay
HOMESTAY_DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5432/homestay
```

**Step 3: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

**Step 4: Verify the API starts**

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/docs  # OpenAPI docs should load
kill %1
```

**Step 5: Verify MCP server starts**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | uv run python -m mcp_server.server
```

Expected: Returns MCP initialization response.

**Step 6: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add Docker Compose for local PostgreSQL and env example"
```

---

### Task 14: Run all tests, push to remote

**Step 1: Run full test suite**

```bash
uv run pytest -v --tb=short
```

Expected: All tests pass (approximately 30+ tests).

**Step 2: Push to remote**

```bash
git push -u origin master
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | Project scaffolding, deps, config, test fixtures | - |
| 2 | SQLAlchemy models (Room, Booking, RoomAvailability) | 3 |
| 3 | Alembic migrations | - |
| 4 | Pydantic schemas and response envelope | 2 |
| 5 | Room service (CRUD + availability generation) | 7 |
| 6 | Availability service (date-range queries) | 3 |
| 7 | Booking service (full lifecycle, conflict prevention) | 10 |
| 8 | FastAPI app + health endpoint | 1 |
| 9 | Rooms API endpoints | 6 |
| 10 | Availability API endpoints | 2 |
| 11 | Bookings API endpoints | 7 |
| 12 | MCP server with all tools | 1 |
| 13 | Docker Compose + integration verification | - |
| 14 | Final test run + push | - |

**Total: ~42 tests across 14 tasks**
