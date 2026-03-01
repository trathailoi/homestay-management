# Homestay Management Frontend Design

**Date:** 2026-03-01
**Status:** Approved

## Overview

Web frontend for the Homestay Management System with two interfaces:
1. **Guest portal** (public) — browse rooms, request bookings
2. **Receptionist dashboard** (authenticated) — manage rooms, bookings, check-ins/outs

## Stack

- **Framework:** Next.js (App Router)
- **UI:** Tailwind CSS + shadcn/ui
- **Location:** `frontend/` directory in monorepo
- **API:** Calls FastAPI backend at `localhost:8000` via Next.js rewrites (no CORS)

## Architecture

```
frontend/
├── app/
│   ├── (guest)/                   # Public guest portal
│   │   ├── page.tsx               # Landing: room search
│   │   ├── rooms/page.tsx         # Search results
│   │   └── book/[roomId]/page.tsx # Booking request form
│   │
│   ├── (receptionist)/            # Auth-protected staff dashboard
│   │   ├── dashboard/page.tsx     # Today's overview
│   │   ├── rooms/page.tsx         # Room list + management
│   │   ├── rooms/[id]/page.tsx    # Room detail + calendar
│   │   ├── bookings/page.tsx      # Booking list + search
│   │   └── bookings/[id]/page.tsx # Booking detail + actions
│   │
│   ├── login/page.tsx             # Receptionist login
│   └── layout.tsx                 # Root layout
├── components/                    # Shared UI components
├── lib/api.ts                     # API client wrapper
└── package.json
```

- Server components for initial data loading
- Client components for interactive elements (forms, status transitions, calendar)
- Separate layouts for guest and receptionist route groups

## Authentication

- Username + password accounts for receptionists
- New `users` table: id, username, password_hash, role, created_at
- JWT token-based sessions stored in httpOnly cookies
- API endpoints: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- Middleware protects all `/api/v1/` receptionist-specific routes
- Guest portal endpoints remain public

## Guest Portal Pages

### 1. Room Search (Landing Page) — `/`

- Date picker: check-in and check-out dates
- Guest count selector
- Calls `GET /api/v1/availability?check_in=...&check_out=...&guests=...`
- Results displayed as room cards: name, type, amenities tags, max occupancy, total price
- "Request Booking" button per room

### 2. Booking Request Form — `/book/[roomId]`

- Pre-filled: room info, dates, price from search
- Guest fills in: name, email, phone, number of guests, special requests
- Submits `POST /api/v1/bookings` — creates booking with status `pending`
- Confirmation page: "Your request has been submitted. The homestay will confirm shortly."

## Receptionist Dashboard Pages

### 3. Today's Dashboard — `/dashboard`

Four sections:

- **Arrivals today** — confirmed bookings with check_in_date = today. Each has a "Check In" button.
- **Departures today** — checked_in bookings with check_out_date = today. Each has a "Check Out" button.
- **Pending requests** — bookings with status = pending. Each has "Confirm" and "Reject" buttons.
- **Occupancy summary** — rooms occupied / total active rooms, rooms in maintenance count.

### 4. Room Management — `/rooms`

- Data table: room number, type, name, max occupancy, base price, status, actions
- **Lock/Unlock toggle**: switches room status between `active` and `maintenance` via `PATCH /api/v1/rooms/{id}` with `{"status": "maintenance"|"active"}`
- Create room button → modal with room creation form
- Row click → navigates to room detail page

### 5. Room Detail + Calendar — `/rooms/[id]`

- Editable room info card (name, description, price, amenities, max occupancy)
- Monthly calendar view using `GET /api/v1/availability/rooms/{id}?start_date=...&end_date=...`
- Day colors: green (available), red (booked), gray (room in maintenance)
- Booked days show guest name on hover, click navigates to booking detail
- Month navigation (previous/next)

### 6. Booking List — `/bookings`

- Filterable data table with columns: guest name, room number, check-in, check-out, status, total amount
- **Search** by guest name or phone (requires new backend query param)
- **Filters:** status dropdown, date range picker
- **Quick actions** per row: confirm, check-in, check-out, cancel (contextual based on current status)
- Pagination

### 7. Booking Detail — `/bookings/[id]`

- Full booking information display
- Status badge with contextual action buttons (only valid transitions shown)
- **Early check-in / late check-out section:**
  - Toggle for early check-in with optional fee amount
  - Toggle for late check-out with optional fee amount
  - Stored as structured `additional_fees` JSON on booking
- Special requests display
- Cancel button → modal with reason text input
- Link to room detail

## Backend Changes Required

### New: Users & Auth
- `users` table: id (UUID), username (unique), password_hash, role (enum: admin, receptionist), created_at, updated_at
- Password hashing with bcrypt via `passlib`
- JWT tokens via `python-jose` or `pyjwt`
- Auth endpoints under `/api/v1/auth/`
- Auth middleware for receptionist routes

### New: Additional Fees on Bookings
- Add `additional_fees` column (JSON) to bookings table
  - Schema: `[{"type": "early_checkin"|"late_checkout"|"other", "description": str, "amount": Decimal}]`
- Alembic migration for the new column
- Update BookingUpdate schema to accept additional_fees
- Update BookingResponse schema to include additional_fees

### New: Booking Search
- Add `guest_search` query parameter to `GET /api/v1/bookings`
- Searches guest_name and guest_phone with case-insensitive ILIKE

### New: CORS Configuration
- Add CORS middleware to FastAPI for development (Next.js dev server on port 3000)
- Production uses reverse proxy (no CORS needed)

## Data Flow

```
Guest searches rooms
  → GET /availability?check_in&check_out&guests
  → Display available rooms with total prices

Guest requests booking
  → POST /bookings (status: pending)
  → Receptionist sees it in dashboard pending section

Receptionist confirms
  → POST /bookings/{id}/confirm (status: confirmed)

Receptionist checks guest in (on check-in date)
  → POST /bookings/{id}/check-in (status: checked_in)
  → Can add early check-in fee via PATCH /bookings/{id}

Receptionist checks guest out
  → POST /bookings/{id}/check-out (status: checked_out)
  → Can add late check-out fee via PATCH /bookings/{id}
  → Future dates released automatically

Receptionist locks room for maintenance
  → PATCH /rooms/{id} {"status": "maintenance"}
  → Room excluded from availability searches

Receptionist cancels booking
  → POST /bookings/{id}/cancel {"reason": "..."}
  → Availability dates released
```

## Component Library (shadcn/ui)

Key components to use:
- **Calendar** — room availability calendar
- **Data Table** — room list, booking list (sortable, filterable)
- **Dialog/Sheet** — create room modal, cancel reason modal
- **Form + Input** — booking form, room form
- **Badge** — booking status, room status
- **Card** — room cards in guest search, dashboard sections
- **Date Picker** — check-in/check-out selection
- **Tabs** — dashboard sections
- **Toast** — success/error notifications on actions
