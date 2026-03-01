# Homestay Management System - Design Document

## Overview

A homestay management API that handles room inventory, availability checking, and booking/reservation lifecycle. Exposes both a REST API (with OpenAPI spec) and an MCP server so AI agents can interact with it directly.

## Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI (async, auto-generated OpenAPI 3.1)
- **ORM:** SQLAlchemy (async)
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **MCP SDK:** `mcp` (Python)

## Architecture

```
REST API (FastAPI)  ──┐
                      ├──> Service Layer ──> SQLAlchemy ──> PostgreSQL
MCP Server           ──┘
```

The service layer contains all business logic. Both the REST API handlers and MCP tools call into the same service layer. This avoids duplicating logic and ensures consistency.

### Project Structure

```
homestay-management/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Settings (DB URL, etc.)
│   ├── database.py           # SQLAlchemy engine & session
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── room.py
│   │   ├── booking.py
│   │   └── room_availability.py
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── room.py
│   │   ├── booking.py
│   │   └── availability.py
│   ├── api/                  # REST API route handlers
│   │   ├── rooms.py
│   │   ├── bookings.py
│   │   └── availability.py
│   └── services/             # Business logic
│       ├── room_service.py
│       ├── booking_service.py
│       └── availability_service.py
├── mcp_server/               # MCP server (separate entry point)
│   ├── server.py
│   └── tools.py              # MCP tools wrapping the service layer
├── alembic/                  # DB migrations
├── tests/
├── alembic.ini
├── pyproject.toml
└── docker-compose.yml        # PostgreSQL for local dev
```

## Data Models

### rooms

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| room_number | VARCHAR(20) | Unique |
| room_type | VARCHAR(50) | e.g. "standard", "deluxe" |
| name | VARCHAR(100) | Display name |
| description | TEXT | Optional |
| max_occupancy | INTEGER | Max guests |
| base_price_per_night | DECIMAL(10,2) | Default nightly rate |
| amenities | JSONB | e.g. `["wifi", "ac", "parking"]` |
| status | VARCHAR(20) | `active`, `maintenance`, `inactive` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### bookings

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| room_id | UUID | FK -> rooms |
| guest_name | VARCHAR(200) | Guest name |
| guest_phone | VARCHAR(50) | Mandatory contact phone |
| check_in_date | DATE | |
| check_out_date | DATE | |
| num_guests | INTEGER | |
| total_amount | DECIMAL(10,2) | Calculated from nights * rate |
| status | VARCHAR(20) | `pending`, `confirmed`, `cancelled`, `checked_in`, `checked_out` |
| special_requests | TEXT | Optional |
| idempotency_key | VARCHAR(100) | Unique, for safe retries |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### room_availability

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| room_id | UUID | FK -> rooms |
| date | DATE | The specific date |
| is_available | BOOLEAN | Default true |
| booking_id | UUID | FK -> bookings, nullable |

Composite unique constraint on `(room_id, date)`.

## Booking Status State Machine

```
pending -> confirmed -> checked_in -> checked_out
   |          |
   +-> cancelled (from pending or confirmed)
```

## API Endpoints

All responses use a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": { "total": 10, "page": 1, "per_page": 20 }
}
```

Errors use semantic error codes:

```json
{
  "success": false,
  "error": {
    "code": "ROOM_NOT_AVAILABLE",
    "message": "Room 101 is not available for 2026-03-15 to 2026-03-18",
    "details": { "room_id": "...", "next_available_date": "2026-03-20" }
  }
}
```

### Rooms

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rooms` | List rooms (filter by type, status) |
| GET | `/api/v1/rooms/{id}` | Get room details |
| POST | `/api/v1/rooms` | Create a room |
| PUT | `/api/v1/rooms/{id}` | Update room details |
| DELETE | `/api/v1/rooms/{id}` | Deactivate a room |

### Availability

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/availability` | Query available rooms for date range |
| GET | `/api/v1/rooms/{id}/availability` | Get room availability calendar |

### Bookings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/bookings` | List bookings (filter by status, date, room) |
| GET | `/api/v1/bookings/{id}` | Get booking details |
| POST | `/api/v1/bookings` | Create a booking (with idempotency key) |
| PUT | `/api/v1/bookings/{id}` | Modify a booking |
| POST | `/api/v1/bookings/{id}/confirm` | Confirm a pending booking |
| POST | `/api/v1/bookings/{id}/cancel` | Cancel a booking |
| POST | `/api/v1/bookings/{id}/check-in` | Check in |
| POST | `/api/v1/bookings/{id}/check-out` | Check out |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |

## MCP Server Tools

| Tool Name | Description |
|-----------|-------------|
| `list_rooms` | List all rooms with optional filters |
| `get_room` | Get details of a specific room |
| `check_availability` | Check room availability for a date range |
| `create_booking` | Create a new booking |
| `get_booking` | Get booking details |
| `list_bookings` | List bookings with filters |
| `confirm_booking` | Confirm a pending booking |
| `cancel_booking` | Cancel a booking |
| `check_in` | Check in a guest |
| `check_out` | Check out a guest |

The MCP server runs as a separate process using stdio transport. It imports the same service layer as the REST API and shares the same database.

## Key Business Logic

### Booking Creation

1. Validate inputs (dates, room exists, guest count <= max_occupancy)
2. Check idempotency key -- if a booking with this key exists, return it
3. Within a database transaction:
   - Query `room_availability` for the requested date range with `SELECT ... FOR UPDATE`
   - If any date is unavailable, return error with `ROOM_NOT_AVAILABLE` and `next_available_date`
   - Set `is_available = false` and link `booking_id` for each date
   - Create the booking record with status `pending`
4. Return the created booking

### Availability Query

1. Accept `check_in`, `check_out`, and optional `guests` filter
2. Find rooms where ALL dates in the range are available and `max_occupancy >= guests`
3. Return matching rooms with their nightly rate

### Room Creation

When a room is created, auto-generate `room_availability` rows for the next 365 days (all available).

### Cancellation

1. Set booking status to `cancelled`
2. Release all dates in `room_availability` (set `is_available = true`, clear `booking_id`)

## Authentication

No auth for MVP. Will add API key authentication in a future iteration.

## AI-Agent Friendliness

- OpenAPI 3.1 spec auto-generated by FastAPI
- Consistent response envelope on all endpoints
- Semantic error codes with actionable details
- Idempotency key support on booking creation
- MCP server for direct AI assistant integration
- Clear, descriptive parameter names and documentation
