# Homestay Management Frontend Implementation Plan


**Goal:** Build a Next.js frontend with a guest portal (public room search + booking requests) and a receptionist dashboard (room management, booking lifecycle, calendar view) backed by the existing FastAPI API.

**Architecture:** Monorepo with `frontend/` directory. Next.js App Router with route groups: `(guest)` for public pages and `(receptionist)` for auth-protected pages. API calls proxied through Next.js rewrites to FastAPI at port 8000. Backend extended with user auth, guest search, additional fees, and CORS.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, bcrypt + JWT for auth, SQLAlchemy + Alembic for backend changes.

---

## Phase 1: Backend Extensions

### Task 1: User Model and Auth Endpoints

**Files:**
- Create: `app/models/user.py`
- Modify: `app/models/__init__.py`
- Create: `app/schemas/auth.py`
- Create: `app/services/auth_service.py`
- Create: `app/api/auth.py`
- Modify: `app/main.py`
- Modify: `pyproject.toml`
- Test: `tests/test_auth.py`

**Step 1: Add auth dependencies to pyproject.toml**

Add `passlib[bcrypt]` and `pyjwt` to `[project.dependencies]`:

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.0.0",
    "fastmcp>=2.10.5",
    "passlib[bcrypt]>=1.7.4",
    "pyjwt>=2.9.0",
]
```

Run: `uv sync --all-extras`

**Step 2: Add auth settings to app/config.py**

Add to `Settings` class:

```python
# Auth
jwt_secret_key: str = "change-me-in-production"
jwt_algorithm: str = "HS256"
jwt_expire_minutes: int = 480  # 8 hours
```

**Step 3: Create User model in `app/models/user.py`**

```python
"""User ORM model for receptionist authentication."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """User model for staff accounts."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="receptionist")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

**Step 4: Update `app/models/__init__.py`**

Add `User` to the imports and `__all__`:

```python
from app.models.user import User
```

**Step 5: Create auth schemas in `app/schemas/auth.py`**

```python
"""Pydantic schemas for authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


class RegisterRequest(BaseModel):
    """Register request body (admin only)."""
    username: str = Field(max_length=100)
    password: str = Field(min_length=6, max_length=200)
    role: str = Field(default="receptionist")


class TokenResponse(BaseModel):
    """Login response with JWT token."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""
    model_config = {"from_attributes": True}

    id: UUID
    username: str
    role: str
    created_at: datetime
```

**Step 6: Create auth service in `app/services/auth_service.py`**

```python
"""Authentication service for user management and JWT tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import HomestayError
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(HomestayError):
    """Raised on invalid credentials."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthService:
    """Handles user authentication and JWT token management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, username: str, password: str, role: str = "receptionist") -> User:
        """Create a new user account."""
        existing = await self.session.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise HomestayError(
                message=f"Username '{username}' already exists",
                code="USERNAME_EXISTS",
            )

        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role=role,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, username: str, password: str) -> User:
        """Verify credentials and return user."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(password, user.password_hash):
            raise AuthenticationError()
        return user

    @staticmethod
    def create_token(user_id: UUID, role: str) -> str:
        """Create a JWT access token."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user_id),
            "role": role,
            "exp": expire,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token."""
        try:
            return jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError("User not found")
        return user
```

**Step 7: Create auth API routes in `app/api/auth.py`**

```python
"""Authentication API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[TokenResponse]:
    """Login and receive JWT token (also set as httpOnly cookie)."""
    service = AuthService(session)
    user = await service.authenticate(data.username, data.password)
    token = service.create_token(user.id, user.role)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    return SuccessResponse(data=TokenResponse(access_token=token))


@router.post("/logout")
async def logout(response: Response) -> SuccessResponse[dict]:
    """Clear auth cookie."""
    response.delete_cookie(key="access_token")
    return SuccessResponse(data={"message": "Logged out"})


@router.get("/me")
async def get_current_user(
    access_token: str | None = Cookie(None),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UserResponse]:
    """Get currently authenticated user."""
    if not access_token:
        from app.services.auth_service import AuthenticationError
        raise AuthenticationError("Not authenticated")

    service = AuthService(session)
    payload = service.decode_token(access_token)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.post("/register")
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UserResponse]:
    """Register a new user account."""
    service = AuthService(session)
    user = await service.register(data.username, data.password, data.role)
    return SuccessResponse(data=UserResponse.model_validate(user))


# Import settings at module level for cookie config
from app.config import settings  # noqa: E402
```

**Step 8: Register auth router and exception handler in `app/main.py`**

Add to imports:

```python
from app.api.auth import router as auth_router
from app.services.auth_service import AuthenticationError
```

Add router:

```python
app.include_router(auth_router, prefix="/api/v1")
```

Add exception handler:

```python
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
        },
    )
```

**Step 9: Write tests in `tests/test_auth.py`**

```python
"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def registered_user(client: AsyncClient):
    """Register a test user and return credentials."""
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
        "role": "receptionist",
    })
    assert resp.status_code == 200
    return {"username": "testuser", "password": "testpass123"}


async def test_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "password": "securepass",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "newuser"


async def test_register_duplicate(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "other",
    })
    assert resp.status_code == 400 or resp.json()["success"] is False


async def test_login_success(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/login", json=registered_user)
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


async def test_login_wrong_password(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


async def test_me_with_cookie(client: AsyncClient, registered_user):
    login_resp = await client.post("/api/v1/auth/login", json=registered_user)
    token = login_resp.json()["data"]["access_token"]
    resp = await client.get("/api/v1/auth/me", cookies={"access_token": token})
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "testuser"


async def test_me_no_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
```

**Step 10: Run tests**

Run: `uv run pytest tests/test_auth.py -v --override-ini="addopts="`
Expected: All 6 tests PASS

**Step 11: Generate Alembic migration**

```bash
uv run alembic revision --autogenerate -m "add users table"
uv run alembic upgrade head
```

**Step 12: Seed an admin user**

Create `scripts/seed_admin.py`:

```python
"""Seed initial admin user."""

import asyncio
from app.database import SessionLocal
from app.services.auth_service import AuthService


async def main():
    async with SessionLocal() as session:
        service = AuthService(session)
        try:
            user = await service.register("admin", "admin123", "admin")
            print(f"Admin user created: {user.username}")
        except Exception as e:
            print(f"Admin already exists or error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

Run: `uv run python scripts/seed_admin.py`

**Step 13: Commit**

```bash
git add app/models/user.py app/schemas/auth.py app/services/auth_service.py \
  app/api/auth.py app/models/__init__.py app/main.py app/config.py \
  pyproject.toml tests/test_auth.py scripts/seed_admin.py \
  alembic/versions/
git commit -m "feat: add user authentication with JWT tokens and cookie sessions"
```

---

### Task 2: Additional Fees on Bookings

**Files:**
- Modify: `app/models/booking.py`
- Modify: `app/schemas/booking.py`
- Modify: `app/api/bookings.py`
- Test: `tests/test_additional_fees.py`

**Step 1: Add `additional_fees` column to Booking model**

In `app/models/booking.py`, add after `cancellation_reason`:

```python
additional_fees: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

Add `JSON` to the SQLAlchemy imports:

```python
from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
```

**Step 2: Add fee schema and update booking schemas in `app/schemas/booking.py`**

Add the fee model and update BookingUpdate and BookingResponse:

```python
class AdditionalFee(BaseModel):
    """A single additional fee line item."""
    type: str  # "early_checkin", "late_checkout", "other"
    description: str
    amount: Decimal = Field(ge=0)
```

Add to `BookingUpdate`:

```python
additional_fees: list[AdditionalFee] | None = None
```

Add to `BookingResponse`:

```python
additional_fees: list[dict] | None
```

**Step 3: Update `_booking_to_response` in `app/api/bookings.py`**

Add the additional_fees field:

```python
additional_fees=booking.additional_fees,
```

**Step 4: Write tests in `tests/test_additional_fees.py`**

```python
"""Tests for additional fees on bookings."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def room_and_booking(client: AsyncClient):
    """Create a room and booking for testing."""
    room_resp = await client.post("/api/v1/rooms", json={
        "room_number": "FEE-101",
        "room_type": "standard",
        "name": "Fee Test Room",
        "max_occupancy": 2,
        "base_price_per_night": "100.00",
    })
    room_id = room_resp.json()["data"]["id"]

    booking_resp = await client.post("/api/v1/bookings", json={
        "room_id": room_id,
        "guest_name": "Fee Tester",
        "guest_phone": "555-0000",
        "check_in_date": "2026-04-10",
        "check_out_date": "2026-04-12",
        "num_guests": 1,
    })
    booking_id = booking_resp.json()["data"]["id"]
    return room_id, booking_id


async def test_add_additional_fees(client: AsyncClient, room_and_booking):
    _, booking_id = room_and_booking
    resp = await client.patch(f"/api/v1/bookings/{booking_id}", json={
        "additional_fees": [
            {"type": "early_checkin", "description": "Early check-in at 10am", "amount": "25.00"},
            {"type": "late_checkout", "description": "Late check-out until 3pm", "amount": "0.00"},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["additional_fees"]) == 2
    assert data["additional_fees"][0]["type"] == "early_checkin"


async def test_booking_response_includes_fees(client: AsyncClient, room_and_booking):
    _, booking_id = room_and_booking
    await client.patch(f"/api/v1/bookings/{booking_id}", json={
        "additional_fees": [
            {"type": "other", "description": "Extra towels", "amount": "5.00"},
        ]
    })
    resp = await client.get(f"/api/v1/bookings/{booking_id}")
    assert resp.json()["data"]["additional_fees"] is not None
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_additional_fees.py -v --override-ini="addopts="`
Expected: PASS

**Step 6: Generate migration and commit**

```bash
uv run alembic revision --autogenerate -m "add additional_fees to bookings"
uv run alembic upgrade head
git add app/models/booking.py app/schemas/booking.py app/api/bookings.py \
  tests/test_additional_fees.py alembic/versions/
git commit -m "feat: add structured additional_fees column to bookings"
```

---

### Task 3: Guest Search and CORS

**Files:**
- Modify: `app/services/booking_service.py`
- Modify: `app/api/bookings.py`
- Modify: `app/main.py`
- Test: `tests/test_guest_search.py`

**Step 1: Add `guest_search` parameter to `BookingService.list_bookings`**

In `app/services/booking_service.py`, update `list_bookings` signature to add:

```python
guest_search: str | None = None,
```

Add filter logic after the existing filters (before pagination):

```python
if guest_search:
    search_term = f"%{guest_search}%"
    query = query.where(
        Booking.guest_name.ilike(search_term)
        | Booking.guest_phone.ilike(search_term)
    )
```

**Step 2: Add `guest_search` query param to bookings route**

In `app/api/bookings.py`, update `list_bookings` to add `guest_search: str | None = None` parameter and pass it to the service.

**Step 3: Add CORS middleware to `app/main.py`**

Add after app creation:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 4: Write tests in `tests/test_guest_search.py`**

```python
"""Tests for guest search on bookings endpoint."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def bookings_for_search(client: AsyncClient):
    """Create room and multiple bookings for search testing."""
    room_resp = await client.post("/api/v1/rooms", json={
        "room_number": "SRCH-101",
        "room_type": "standard",
        "name": "Search Test Room",
        "max_occupancy": 4,
        "base_price_per_night": "80.00",
    })
    room_id = room_resp.json()["data"]["id"]

    await client.post("/api/v1/bookings", json={
        "room_id": room_id,
        "guest_name": "Alice Johnson",
        "guest_phone": "555-1111",
        "check_in_date": "2026-05-01",
        "check_out_date": "2026-05-03",
        "num_guests": 1,
    })
    await client.post("/api/v1/bookings", json={
        "room_id": room_id,
        "guest_name": "Bob Smith",
        "guest_phone": "555-2222",
        "check_in_date": "2026-05-05",
        "check_out_date": "2026-05-07",
        "num_guests": 2,
    })
    return room_id


async def test_search_by_name(client: AsyncClient, bookings_for_search):
    resp = await client.get("/api/v1/bookings", params={"guest_search": "alice"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["guest_name"] == "Alice Johnson"


async def test_search_by_phone(client: AsyncClient, bookings_for_search):
    resp = await client.get("/api/v1/bookings", params={"guest_search": "555-2222"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["guest_name"] == "Bob Smith"


async def test_search_no_match(client: AsyncClient, bookings_for_search):
    resp = await client.get("/api/v1/bookings", params={"guest_search": "nonexistent"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 0
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_guest_search.py -v --override-ini="addopts="`
Expected: PASS

**Step 6: Commit**

```bash
git add app/services/booking_service.py app/api/bookings.py app/main.py \
  tests/test_guest_search.py
git commit -m "feat: add guest name/phone search and CORS middleware"
```

---

## Phase 2: Frontend Scaffolding

### Task 4: Initialize Next.js Project

**Files:**
- Create: `frontend/` directory with Next.js scaffolding

**Step 1: Create Next.js app**

```bash
cd /tmp/homestay-management
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-import-alias \
  --turbopack
```

**Step 2: Install shadcn/ui**

```bash
cd frontend
npx shadcn@latest init -d
```

When prompted: style=new-york, color=neutral, css-variables=yes.

**Step 3: Add shadcn components we need**

```bash
npx shadcn@latest add button card input label dialog table badge \
  calendar select textarea toast tabs sheet separator dropdown-menu \
  popover form
```

**Step 4: Configure API proxy in `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
```

**Step 5: Create API client in `frontend/src/lib/api.ts`**

```typescript
const API_BASE = "/api/v1";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: { total: number; page: number; per_page: number };
}

export interface ApiError {
  success: false;
  error: { code: string; message: string; details?: Record<string, unknown> };
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    credentials: "include",
  });

  const json = await res.json();

  if (!res.ok || !json.success) {
    throw json as ApiError;
  }

  return json;
}
```

**Step 6: Create TypeScript types in `frontend/src/lib/types.ts`**

```typescript
export interface Room {
  id: string;
  room_number: string;
  room_type: string;
  name: string;
  description: string | null;
  max_occupancy: number;
  base_price_per_night: number;
  amenities: string[] | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  room_id: string;
  room_number: string;
  guest_name: string;
  guest_phone: string;
  check_in_date: string;
  check_out_date: string;
  num_guests: number;
  total_amount: string;
  status: string;
  special_requests: string | null;
  idempotency_key: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  additional_fees: AdditionalFee[] | null;
  created_at: string;
  updated_at: string;
}

export interface AdditionalFee {
  type: string;
  description: string;
  amount: string;
}

export interface AvailableRoom {
  id: string;
  room_number: string;
  room_type: string;
  name: string;
  max_occupancy: number;
  base_price_per_night: string;
  amenities: string[] | null;
  total_price: number;
}

export interface RoomAvailabilityDay {
  date: string;
  is_available: boolean;
  booking_id: string | null;
}

export interface User {
  id: string;
  username: string;
  role: string;
  created_at: string;
}
```

**Step 7: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000 — should show Next.js default page.

**Step 8: Commit**

```bash
cd /tmp/homestay-management
git add frontend/
git commit -m "feat: scaffold Next.js frontend with shadcn/ui and API client"
```

---

### Task 5: Auth Context and Login Page

**Files:**
- Create: `frontend/src/lib/auth-context.tsx`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/components/auth-guard.tsx`

**Step 1: Create auth context in `frontend/src/lib/auth-context.tsx`**

```tsx
"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { apiFetch } from "./api";
import { User } from "./types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<User>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    const res = await apiFetch<User>("/auth/me");
    setUser(res.data);
  };

  const logout = async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

**Step 2: Create auth guard in `frontend/src/components/auth-guard.tsx`**

```tsx
"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) return null;

  return <>{children}</>;
}
```

**Step 3: Create login page in `frontend/src/app/login/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.push("/dashboard");
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Homestay Management</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 4: Update root layout in `frontend/src/app/layout.tsx`**

Wrap with AuthProvider:

```tsx
import { AuthProvider } from "@/lib/auth-context";

// Inside the RootLayout component, wrap {children} with:
<AuthProvider>{children}</AuthProvider>
```

**Step 5: Verify login flow works**

1. Start backend: `uv run uvicorn app.main:app --reload`
2. Seed admin: `uv run python scripts/seed_admin.py`
3. Start frontend: `cd frontend && npm run dev`
4. Open http://localhost:3000/login — login with admin/admin123

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add auth context, login page, and auth guard"
```

---

## Phase 3: Receptionist Dashboard

### Task 6: Dashboard Layout and Navigation

**Files:**
- Create: `frontend/src/app/(receptionist)/layout.tsx`
- Create: `frontend/src/components/nav-sidebar.tsx`

**Step 1: Create receptionist layout with sidebar**

`frontend/src/app/(receptionist)/layout.tsx`:

```tsx
"use client";

import { AuthGuard } from "@/components/auth-guard";
import { NavSidebar } from "@/components/nav-sidebar";

export default function ReceptionistLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen">
        <NavSidebar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
```

**Step 2: Create sidebar navigation in `frontend/src/components/nav-sidebar.tsx`**

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/rooms", label: "Rooms" },
  { href: "/bookings", label: "Bookings" },
];

export function NavSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex w-56 flex-col border-r bg-muted/40 p-4">
      <h2 className="mb-6 text-lg font-semibold">Homestay</h2>
      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent",
              pathname.startsWith(item.href) && "bg-accent font-medium"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="border-t pt-4">
        <p className="mb-2 text-xs text-muted-foreground">{user?.username}</p>
        <Button variant="outline" size="sm" onClick={logout} className="w-full">
          Sign out
        </Button>
      </div>
    </aside>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add receptionist layout with sidebar navigation"
```

---

### Task 7: Today's Dashboard Page

**Files:**
- Create: `frontend/src/app/(receptionist)/dashboard/page.tsx`

**Step 1: Build dashboard page**

`frontend/src/app/(receptionist)/dashboard/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Booking, Room } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function today() {
  return new Date().toISOString().split("T")[0];
}

export default function DashboardPage() {
  const [arrivals, setArrivals] = useState<Booking[]>([]);
  const [departures, setDepartures] = useState<Booking[]>([]);
  const [pending, setPending] = useState<Booking[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    const todayStr = today();
    const [arrivalsRes, departuresRes, pendingRes, roomsRes] = await Promise.all([
      apiFetch<Booking[]>(`/bookings?status=confirmed&check_in_from=${todayStr}&check_in_to=${todayStr}`),
      apiFetch<Booking[]>(`/bookings?status=checked_in`),
      apiFetch<Booking[]>(`/bookings?status=pending`),
      apiFetch<Room[]>(`/rooms`),
    ]);

    setArrivals(arrivalsRes.data);
    setDepartures(departuresRes.data.filter((b) => b.check_out_date === todayStr));
    setPending(pendingRes.data);
    setRooms(roomsRes.data);
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const handleAction = async (bookingId: string, action: string) => {
    await apiFetch(`/bookings/${bookingId}/${action}`, { method: "POST" });
    fetchData();
  };

  const handleCancel = async (bookingId: string) => {
    await apiFetch(`/bookings/${bookingId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason: "Rejected by receptionist" }),
    });
    fetchData();
  };

  if (loading) return <p>Loading dashboard...</p>;

  const activeRooms = rooms.filter((r) => r.status === "active").length;
  const maintenanceRooms = rooms.filter((r) => r.status === "maintenance").length;
  const checkedInBookings = departures.length; // Using full checked_in list for occupancy

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Occupancy Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Occupied</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{checkedInBookings} / {activeRooms}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Maintenance</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{maintenanceRooms}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Pending Requests</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{pending.length}</p></CardContent>
        </Card>
      </div>

      {/* Arrivals Today */}
      <Card>
        <CardHeader><CardTitle>Arrivals Today</CardTitle></CardHeader>
        <CardContent>
          {arrivals.length === 0 ? <p className="text-muted-foreground">No arrivals today</p> : (
            <div className="space-y-2">
              {arrivals.map((b) => (
                <div key={b.id} className="flex items-center justify-between rounded-md border p-3">
                  <div>
                    <p className="font-medium">{b.guest_name}</p>
                    <p className="text-sm text-muted-foreground">Room {b.room_number} &middot; {b.num_guests} guest(s)</p>
                  </div>
                  <Button size="sm" onClick={() => handleAction(b.id, "check-in")}>Check In</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Departures Today */}
      <Card>
        <CardHeader><CardTitle>Departures Today</CardTitle></CardHeader>
        <CardContent>
          {departures.length === 0 ? <p className="text-muted-foreground">No departures today</p> : (
            <div className="space-y-2">
              {departures.map((b) => (
                <div key={b.id} className="flex items-center justify-between rounded-md border p-3">
                  <div>
                    <p className="font-medium">{b.guest_name}</p>
                    <p className="text-sm text-muted-foreground">Room {b.room_number}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => handleAction(b.id, "check-out")}>Check Out</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Requests */}
      <Card>
        <CardHeader><CardTitle>Pending Booking Requests</CardTitle></CardHeader>
        <CardContent>
          {pending.length === 0 ? <p className="text-muted-foreground">No pending requests</p> : (
            <div className="space-y-2">
              {pending.map((b) => (
                <div key={b.id} className="flex items-center justify-between rounded-md border p-3">
                  <div>
                    <p className="font-medium">{b.guest_name}</p>
                    <p className="text-sm text-muted-foreground">
                      Room {b.room_number} &middot; {b.check_in_date} to {b.check_out_date} &middot; ${b.total_amount}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => handleAction(b.id, "confirm")}>Confirm</Button>
                    <Button size="sm" variant="destructive" onClick={() => handleCancel(b.id)}>Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Verify dashboard renders**

Start both servers, login, and verify http://localhost:3000/dashboard shows the 4 sections.

**Step 3: Commit**

```bash
git add frontend/src/app/\(receptionist\)/dashboard/
git commit -m "feat: add today's dashboard with arrivals, departures, pending requests"
```

---

### Task 8: Room Management Page

**Files:**
- Create: `frontend/src/app/(receptionist)/rooms/page.tsx`
- Create: `frontend/src/components/create-room-dialog.tsx`

**Step 1: Create room list page with lock/unlock toggle**

`frontend/src/app/(receptionist)/rooms/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Room } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { CreateRoomDialog } from "@/components/create-room-dialog";

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRooms = async () => {
    const res = await apiFetch<Room[]>("/rooms");
    setRooms(res.data);
    setLoading(false);
  };

  useEffect(() => { fetchRooms(); }, []);

  const toggleStatus = async (room: Room) => {
    const newStatus = room.status === "active" ? "maintenance" : "active";
    await apiFetch(`/rooms/${room.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus }),
    });
    fetchRooms();
  };

  if (loading) return <p>Loading rooms...</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Rooms</h1>
        <CreateRoomDialog onCreated={fetchRooms} />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Room #</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Capacity</TableHead>
            <TableHead>Price/Night</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rooms.map((room) => (
            <TableRow key={room.id}>
              <TableCell>
                <Link href={`/rooms/${room.id}`} className="font-medium underline">
                  {room.room_number}
                </Link>
              </TableCell>
              <TableCell>{room.name}</TableCell>
              <TableCell>{room.room_type}</TableCell>
              <TableCell>{room.max_occupancy}</TableCell>
              <TableCell>${room.base_price_per_night}</TableCell>
              <TableCell>
                <Badge variant={room.status === "active" ? "default" : "secondary"}>
                  {room.status}
                </Badge>
              </TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant={room.status === "active" ? "outline" : "default"}
                  onClick={() => toggleStatus(room)}
                >
                  {room.status === "active" ? "Lock" : "Unlock"}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

**Step 2: Create room creation dialog in `frontend/src/components/create-room-dialog.tsx`**

```tsx
"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

export function CreateRoomDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    const form = new FormData(e.currentTarget);

    await apiFetch("/rooms", {
      method: "POST",
      body: JSON.stringify({
        room_number: form.get("room_number"),
        room_type: form.get("room_type"),
        name: form.get("name"),
        description: form.get("description") || null,
        max_occupancy: Number(form.get("max_occupancy")),
        base_price_per_night: form.get("base_price_per_night"),
        amenities: (form.get("amenities") as string)
          ?.split(",")
          .map((a) => a.trim())
          .filter(Boolean) || null,
      }),
    });

    setLoading(false);
    setOpen(false);
    onCreated();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add Room</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Room</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="room_number">Room Number</Label>
              <Input id="room_number" name="room_number" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="room_type">Type</Label>
              <Input id="room_type" name="room_type" placeholder="standard" required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" name="name" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" name="description" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_occupancy">Max Occupancy</Label>
              <Input id="max_occupancy" name="max_occupancy" type="number" min={1} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_price_per_night">Price/Night ($)</Label>
              <Input id="base_price_per_night" name="base_price_per_night" type="number" step="0.01" min="0.01" required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="amenities">Amenities (comma-separated)</Label>
            <Input id="amenities" name="amenities" placeholder="wifi, air-conditioning, minibar" />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Creating..." : "Create Room"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add room management page with create dialog and lock/unlock"
```

---

### Task 9: Room Detail and Calendar Page

**Files:**
- Create: `frontend/src/app/(receptionist)/rooms/[id]/page.tsx`
- Create: `frontend/src/components/room-calendar.tsx`

**Step 1: Create room calendar component in `frontend/src/components/room-calendar.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { RoomAvailabilityDay } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  roomId: string;
  roomStatus: string;
}

export function RoomCalendar({ roomId, roomStatus }: Props) {
  const router = useRouter();
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [days, setDays] = useState<RoomAvailabilityDay[]>([]);

  useEffect(() => {
    const startDate = new Date(currentMonth);
    const endDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);

    const fmt = (d: Date) => d.toISOString().split("T")[0];

    apiFetch<RoomAvailabilityDay[]>(
      `/availability/rooms/${roomId}?start_date=${fmt(startDate)}&end_date=${fmt(endDate)}`
    ).then((res) => setDays(res.data));
  }, [roomId, currentMonth]);

  const prevMonth = () =>
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  const nextMonth = () =>
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));

  const monthLabel = currentMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" });

  // Build calendar grid
  const firstDayOfWeek = currentMonth.getDay();
  const daysInMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).getDate();
  const dayMap = new Map(days.map((d) => [d.date, d]));

  const cells: (RoomAvailabilityDay | null)[] = [];
  for (let i = 0; i < firstDayOfWeek; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push(dayMap.get(dateStr) || null);
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={prevMonth}>Previous</Button>
        <h3 className="font-semibold">{monthLabel}</h3>
        <Button variant="outline" size="sm" onClick={nextMonth}>Next</Button>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="p-2 text-center text-xs font-medium text-muted-foreground">{d}</div>
        ))}
        {cells.map((day, i) => {
          if (!day) return <div key={`empty-${i}`} className="p-2" />;

          const dateNum = parseInt(day.date.split("-")[2]);
          const isBooked = !day.is_available && day.booking_id;
          const isMaintenance = roomStatus === "maintenance";

          return (
            <div
              key={day.date}
              className={cn(
                "cursor-pointer rounded p-2 text-center text-sm transition-colors",
                isMaintenance && "bg-muted text-muted-foreground",
                !isMaintenance && day.is_available && "bg-green-100 hover:bg-green-200 dark:bg-green-900/30",
                !isMaintenance && isBooked && "bg-red-100 hover:bg-red-200 dark:bg-red-900/30",
              )}
              onClick={() => {
                if (isBooked && day.booking_id) {
                  router.push(`/bookings/${day.booking_id}`);
                }
              }}
              title={isBooked ? `Booked (click to view)` : day.is_available ? "Available" : "Unavailable"}
            >
              {dateNum}
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="h-3 w-3 rounded bg-green-100 dark:bg-green-900/30" /> Available
        </div>
        <div className="flex items-center gap-1">
          <div className="h-3 w-3 rounded bg-red-100 dark:bg-red-900/30" /> Booked
        </div>
        <div className="flex items-center gap-1">
          <div className="h-3 w-3 rounded bg-muted" /> Maintenance
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Create room detail page in `frontend/src/app/(receptionist)/rooms/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Room } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RoomCalendar } from "@/components/room-calendar";

export default function RoomDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [room, setRoom] = useState<Room | null>(null);

  const fetchRoom = async () => {
    const res = await apiFetch<Room>(`/rooms/${id}`);
    setRoom(res.data);
  };

  useEffect(() => { fetchRoom(); }, [id]);

  const toggleStatus = async () => {
    if (!room) return;
    const newStatus = room.status === "active" ? "maintenance" : "active";
    await apiFetch(`/rooms/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus }),
    });
    fetchRoom();
  };

  if (!room) return <p>Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Room {room.room_number}: {room.name}</h1>
        <div className="flex items-center gap-3">
          <Badge variant={room.status === "active" ? "default" : "secondary"}>
            {room.status}
          </Badge>
          <Button
            variant={room.status === "active" ? "outline" : "default"}
            onClick={toggleStatus}
          >
            {room.status === "active" ? "Lock for Maintenance" : "Unlock Room"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Room Info */}
        <Card>
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div><span className="font-medium">Type:</span> {room.room_type}</div>
            <div><span className="font-medium">Max Occupancy:</span> {room.max_occupancy}</div>
            <div><span className="font-medium">Price/Night:</span> ${room.base_price_per_night}</div>
            {room.description && <div><span className="font-medium">Description:</span> {room.description}</div>}
            {room.amenities && (
              <div className="flex flex-wrap gap-1 pt-1">
                {room.amenities.map((a) => (
                  <Badge key={a} variant="outline">{a}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Calendar */}
        <Card>
          <CardHeader><CardTitle>Availability Calendar</CardTitle></CardHeader>
          <CardContent>
            <RoomCalendar roomId={id} roomStatus={room.status} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add room detail page with monthly availability calendar"
```

---

### Task 10: Booking List Page with Search

**Files:**
- Create: `frontend/src/app/(receptionist)/bookings/page.tsx`

**Step 1: Create booking list with search and filters**

`frontend/src/app/(receptionist)/bookings/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Booking } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

const STATUS_OPTIONS = ["all", "pending", "confirmed", "checked_in", "checked_out", "cancelled"];

const statusVariant = (status: string) => {
  switch (status) {
    case "confirmed": return "default" as const;
    case "checked_in": return "default" as const;
    case "cancelled": return "destructive" as const;
    default: return "secondary" as const;
  }
};

export default function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const fetchBookings = async () => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (search) params.set("guest_search", search);
    const qs = params.toString();

    const res = await apiFetch<Booking[]>(`/bookings${qs ? `?${qs}` : ""}`);
    setBookings(res.data);
    setLoading(false);
  };

  useEffect(() => { fetchBookings(); }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchBookings();
  };

  const handleAction = async (bookingId: string, action: string, body?: object) => {
    await apiFetch(`/bookings/${bookingId}/${action}`, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    fetchBookings();
  };

  if (loading) return <p>Loading bookings...</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Bookings</h1>

      <div className="flex gap-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <Input
            placeholder="Search guest name or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
          <Button type="submit" variant="outline">Search</Button>
        </form>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>{s === "all" ? "All Statuses" : s.replace("_", " ")}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Guest</TableHead>
            <TableHead>Room</TableHead>
            <TableHead>Check-in</TableHead>
            <TableHead>Check-out</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {bookings.map((b) => (
            <TableRow key={b.id}>
              <TableCell>
                <Link href={`/bookings/${b.id}`} className="font-medium underline">
                  {b.guest_name}
                </Link>
                <p className="text-xs text-muted-foreground">{b.guest_phone}</p>
              </TableCell>
              <TableCell>{b.room_number}</TableCell>
              <TableCell>{b.check_in_date}</TableCell>
              <TableCell>{b.check_out_date}</TableCell>
              <TableCell>
                <Badge variant={statusVariant(b.status)}>{b.status.replace("_", " ")}</Badge>
              </TableCell>
              <TableCell>${b.total_amount}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  {b.status === "pending" && (
                    <>
                      <Button size="sm" onClick={() => handleAction(b.id, "confirm")}>Confirm</Button>
                      <Button size="sm" variant="destructive" onClick={() => handleAction(b.id, "cancel", { reason: "Rejected" })}>Reject</Button>
                    </>
                  )}
                  {b.status === "confirmed" && (
                    <Button size="sm" onClick={() => handleAction(b.id, "check-in")}>Check In</Button>
                  )}
                  {b.status === "checked_in" && (
                    <Button size="sm" variant="outline" onClick={() => handleAction(b.id, "check-out")}>Check Out</Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/app/\(receptionist\)/bookings/page.tsx
git commit -m "feat: add booking list page with guest search and status filters"
```

---

### Task 11: Booking Detail Page with Fees

**Files:**
- Create: `frontend/src/app/(receptionist)/bookings/[id]/page.tsx`

**Step 1: Create booking detail page with status actions and fee management**

`frontend/src/app/(receptionist)/bookings/[id]/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Booking, AdditionalFee } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [feeType, setFeeType] = useState("early_checkin");
  const [feeDesc, setFeeDesc] = useState("");
  const [feeAmount, setFeeAmount] = useState("");

  const fetchBooking = async () => {
    const res = await apiFetch<Booking>(`/bookings/${id}`);
    setBooking(res.data);
  };

  useEffect(() => { fetchBooking(); }, [id]);

  const handleAction = async (action: string) => {
    await apiFetch(`/bookings/${id}/${action}`, { method: "POST" });
    fetchBooking();
  };

  const handleCancel = async () => {
    await apiFetch(`/bookings/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason: cancelReason }),
    });
    setCancelOpen(false);
    fetchBooking();
  };

  const handleAddFee = async () => {
    const existingFees: AdditionalFee[] = booking?.additional_fees || [];
    const newFees = [...existingFees, { type: feeType, description: feeDesc, amount: feeAmount }];
    await apiFetch(`/bookings/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ additional_fees: newFees }),
    });
    setFeeType("early_checkin");
    setFeeDesc("");
    setFeeAmount("");
    fetchBooking();
  };

  if (!booking) return <p>Loading...</p>;

  const canConfirm = booking.status === "pending";
  const canCheckIn = booking.status === "confirmed";
  const canCheckOut = booking.status === "checked_in";
  const canCancel = booking.status === "pending" || booking.status === "confirmed";
  const isTerminal = booking.status === "checked_out" || booking.status === "cancelled";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Booking: {booking.guest_name}</h1>
        <Badge variant={booking.status === "cancelled" ? "destructive" : "default"}>
          {booking.status.replace("_", " ")}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Booking Info */}
        <Card>
          <CardHeader><CardTitle>Booking Details</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div><span className="font-medium">Guest:</span> {booking.guest_name}</div>
            <div><span className="font-medium">Phone:</span> {booking.guest_phone}</div>
            <div>
              <span className="font-medium">Room:</span>{" "}
              <Link href={`/rooms/${booking.room_id}`} className="underline">
                {booking.room_number}
              </Link>
            </div>
            <div><span className="font-medium">Check-in:</span> {booking.check_in_date}</div>
            <div><span className="font-medium">Check-out:</span> {booking.check_out_date}</div>
            <div><span className="font-medium">Guests:</span> {booking.num_guests}</div>
            <div><span className="font-medium">Base Amount:</span> ${booking.total_amount}</div>
            {booking.special_requests && (
              <div><span className="font-medium">Special Requests:</span> {booking.special_requests}</div>
            )}
            {booking.cancellation_reason && (
              <div><span className="font-medium">Cancellation Reason:</span> {booking.cancellation_reason}</div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="space-y-4">
          {!isTerminal && (
            <Card>
              <CardHeader><CardTitle>Actions</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {canConfirm && (
                  <Button onClick={() => handleAction("confirm")}>Confirm Booking</Button>
                )}
                {canCheckIn && (
                  <Button onClick={() => handleAction("check-in")}>Check In</Button>
                )}
                {canCheckOut && (
                  <Button variant="outline" onClick={() => handleAction("check-out")}>Check Out</Button>
                )}
                {canCancel && (
                  <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
                    <DialogTrigger asChild>
                      <Button variant="destructive">Cancel Booking</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Cancel Booking</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label>Reason</Label>
                          <Textarea
                            value={cancelReason}
                            onChange={(e) => setCancelReason(e.target.value)}
                            placeholder="Optional cancellation reason..."
                          />
                        </div>
                        <Button variant="destructive" onClick={handleCancel} className="w-full">
                          Confirm Cancellation
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
              </CardContent>
            </Card>
          )}

          {/* Additional Fees */}
          <Card>
            <CardHeader><CardTitle>Additional Fees</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {booking.additional_fees && booking.additional_fees.length > 0 ? (
                <div className="space-y-2">
                  {booking.additional_fees.map((fee, i) => (
                    <div key={i} className="flex items-center justify-between rounded border p-2 text-sm">
                      <div>
                        <span className="font-medium">{fee.type.replace("_", " ")}</span>
                        {fee.description && <span className="text-muted-foreground"> — {fee.description}</span>}
                      </div>
                      <span className="font-medium">${fee.amount}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No additional fees</p>
              )}

              {!isTerminal && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <p className="text-sm font-medium">Add Fee</p>
                    <div className="grid grid-cols-3 gap-2">
                      <select
                        value={feeType}
                        onChange={(e) => setFeeType(e.target.value)}
                        className="rounded border px-2 py-1 text-sm"
                      >
                        <option value="early_checkin">Early Check-in</option>
                        <option value="late_checkout">Late Check-out</option>
                        <option value="other">Other</option>
                      </select>
                      <Input
                        placeholder="Description"
                        value={feeDesc}
                        onChange={(e) => setFeeDesc(e.target.value)}
                        className="text-sm"
                      />
                      <Input
                        placeholder="Amount"
                        type="number"
                        step="0.01"
                        min="0"
                        value={feeAmount}
                        onChange={(e) => setFeeAmount(e.target.value)}
                        className="text-sm"
                      />
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleAddFee}
                      disabled={!feeDesc || !feeAmount}
                    >
                      Add Fee
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/app/\(receptionist\)/bookings/\[id\]/
git commit -m "feat: add booking detail page with status actions and additional fees"
```

---

## Phase 4: Guest Portal

### Task 12: Guest Landing Page (Room Search)

**Files:**
- Create: `frontend/src/app/(guest)/layout.tsx`
- Create: `frontend/src/app/(guest)/page.tsx`

**Step 1: Create guest layout in `frontend/src/app/(guest)/layout.tsx`**

```tsx
export default function GuestLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Homestay</h1>
        <p className="text-muted-foreground">Find and book your perfect room</p>
      </header>
      {children}
    </div>
  );
}
```

**Step 2: Create room search page in `frontend/src/app/(guest)/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { AvailableRoom } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function GuestSearchPage() {
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [guests, setGuests] = useState(1);
  const [rooms, setRooms] = useState<AvailableRoom[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch<AvailableRoom[]>(
        `/availability?check_in=${checkIn}&check_out=${checkOut}&guests=${guests}`
      );
      setRooms(res.data);
    } catch {
      setError("Failed to search. Please check your dates and try again.");
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Search Available Rooms</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="check_in">Check-in</Label>
              <Input
                id="check_in"
                type="date"
                min={today}
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="check_out">Check-out</Label>
              <Input
                id="check_out"
                type="date"
                min={checkIn || today}
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="guests">Guests</Label>
              <Input
                id="guests"
                type="number"
                min={1}
                value={guests}
                onChange={(e) => setGuests(Number(e.target.value))}
                className="w-20"
              />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </Button>
          </form>
          {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
        </CardContent>
      </Card>

      {rooms !== null && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            {rooms.length === 0 ? "No rooms available for these dates" : `${rooms.length} room(s) available`}
          </h2>
          {rooms.map((room) => (
            <Card key={room.id}>
              <CardContent className="flex items-center justify-between p-6">
                <div>
                  <h3 className="text-lg font-semibold">{room.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {room.room_type} &middot; Up to {room.max_occupancy} guests
                  </p>
                  {room.amenities && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {room.amenities.map((a) => (
                        <Badge key={a} variant="outline">{a}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">${room.base_price_per_night}/night</p>
                  <p className="text-2xl font-bold">${room.total_price.toFixed(2)}</p>
                  <p className="mb-2 text-xs text-muted-foreground">total</p>
                  <Link href={`/book/${room.id}?check_in=${checkIn}&check_out=${checkOut}&guests=${guests}`}>
                    <Button>Request Booking</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/app/\(guest\)/
git commit -m "feat: add guest room search page with availability results"
```

---

### Task 13: Guest Booking Request Form

**Files:**
- Create: `frontend/src/app/(guest)/book/[roomId]/page.tsx`

**Step 1: Create booking request form**

`frontend/src/app/(guest)/book/[roomId]/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Booking } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BookingRequestPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const searchParams = useSearchParams();
  const checkIn = searchParams.get("check_in") || "";
  const checkOut = searchParams.get("check_out") || "";
  const guests = searchParams.get("guests") || "1";

  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const form = new FormData(e.currentTarget);

    try {
      await apiFetch<Booking>("/bookings", {
        method: "POST",
        body: JSON.stringify({
          room_id: roomId,
          guest_name: form.get("guest_name"),
          guest_phone: form.get("guest_phone"),
          check_in_date: checkIn,
          check_out_date: checkOut,
          num_guests: Number(guests),
          special_requests: form.get("special_requests") || null,
        }),
      });
      setSubmitted(true);
    } catch (err: unknown) {
      const apiErr = err as { error?: { message?: string } };
      setError(apiErr?.error?.message || "Failed to submit booking request");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <Card className="mx-auto max-w-md">
        <CardContent className="p-8 text-center">
          <h2 className="mb-2 text-xl font-bold">Request Submitted!</h2>
          <p className="text-muted-foreground">
            Your booking request has been submitted. The homestay will review and confirm it shortly.
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            {checkIn} to {checkOut} &middot; {guests} guest(s)
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <CardTitle>Request Booking</CardTitle>
        <p className="text-sm text-muted-foreground">
          {checkIn} to {checkOut} &middot; {guests} guest(s)
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="guest_name">Full Name</Label>
            <Input id="guest_name" name="guest_name" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="guest_phone">Phone Number</Label>
            <Input id="guest_phone" name="guest_phone" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="special_requests">Special Requests (optional)</Label>
            <Textarea
              id="special_requests"
              name="special_requests"
              placeholder="Early check-in, extra pillows, dietary needs..."
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Submitting..." : "Submit Booking Request"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/app/\(guest\)/book/
git commit -m "feat: add guest booking request form with confirmation"
```

---

## Phase 5: Polish and Integration

### Task 14: Root Route Redirect and Final Wiring

**Files:**
- Modify: `frontend/src/app/page.tsx` (remove default Next.js page, redirect to guest portal or keep as guest landing)
- Modify: `frontend/src/app/layout.tsx` (ensure AuthProvider wraps everything)

**Step 1: Update root `page.tsx`**

Since the guest portal lives at `(guest)/page.tsx`, the root `frontend/src/app/page.tsx` will conflict. Delete or replace the default Next.js page:

```tsx
import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/");
}
```

Note: Actually, the `(guest)` route group maps to `/` already since `(guest)/page.tsx` handles the root. Remove the conflicting `app/page.tsx` if Next.js created one outside the route groups. If both exist, delete `app/page.tsx` — the `(guest)/page.tsx` will serve `/`.

**Step 2: Run full integration test**

1. Start backend: `uv run uvicorn app.main:app --reload`
2. Seed admin: `uv run python scripts/seed_admin.py`
3. Start frontend: `cd frontend && npm run dev`
4. Test guest flow: Search rooms at http://localhost:3000, submit a booking request
5. Test receptionist flow: Login at http://localhost:3000/login, check dashboard, confirm the pending booking, manage rooms

**Step 3: Final commit**

```bash
git add frontend/
git commit -m "feat: complete frontend with guest portal and receptionist dashboard"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1: Backend Extensions | 1-3 | User auth (JWT), additional_fees column, guest search, CORS |
| 2: Frontend Scaffolding | 4-5 | Next.js + shadcn/ui project, API client, auth flow |
| 3: Receptionist Dashboard | 6-11 | Layout, dashboard, room mgmt, calendar, booking list, booking detail |
| 4: Guest Portal | 12-13 | Room search, booking request form |
| 5: Polish | 14 | Root routing, integration testing |
