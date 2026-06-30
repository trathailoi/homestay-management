# Monthly Availability Grid — Design

**Date:** 2026-06-30
**Status:** Approved (brainstorm)

## Problem

Admins/receptionists need to see room availability for a whole month at a glance —
a matrix of rooms × days, like the Marriott stop-sale chart. Each cell shows
booking status by color and is clickable to view booking details or create a new
reservation. We do **not** use length-of-stay holds (LS2/LS3/LS5); omit them.

## Decisions

- **Rows** = individual rooms (one row per `room_number`). Matches the data model.
- **Columns** = each day of the selected month.
- **Multi-night bookings** = per-cell color (each occupied night colored
  independently). No continuous span bars.
- **Empty (available) cells** = click-drag to select a contiguous range within one
  room row, then open a new-booking modal.
- **Occupied cells** = popover with booking summary + actions (stay on grid).
- **Color coding** = per booking status (not just available/booked/maintenance).

## Architecture

### 1. Backend — new endpoint

`GET /availability/grid?month=YYYY-MM`

New service method `AvailabilityService.get_month_grid(year, month)`:

1. Load all rooms where `status != "inactive"`, ordered by `room_number`.
2. Load `RoomAvailability` rows for the month where `is_available == False`,
   joined to `Booking` for `status` and `guest_name`.
3. Build, per room, a `days` map keyed by ISO date string for **occupied days
   only**. Available days are simply absent from the map.

`room.status == "maintenance"` is returned as the room's `status`; the frontend
renders the whole row gray. This overrides per-day state.

**Response shape** (`SuccessResponse[list[RoomMonthGrid]]`):

```json
[
  {
    "room_id": "uuid",
    "room_number": "101",
    "name": "Garden Deluxe",
    "room_type": "deluxe",
    "status": "active",
    "days": {
      "2026-06-03": { "state": "confirmed", "booking_id": "uuid", "guest_name": "Lan" },
      "2026-06-04": { "state": "confirmed", "booking_id": "uuid", "guest_name": "Lan" }
    }
  }
]
```

New schemas in `app/schemas/availability.py`:

- `GridCell { state: str, booking_id: UUID, guest_name: str }`
- `RoomMonthGrid { room_id, room_number, name, room_type, status, days: dict[str, GridCell] }`

`state` ∈ `pending | confirmed | checked_in | checked_out`. (`cancelled` and
`checked_out` already free the `RoomAvailability` rows per existing booking-service
logic, so `cancelled` will not appear; `checked_out` may appear only if a row is
still flagged — render it as a neutral/past state.)

One DB query for the blocked rows plus one for the room list. No N+1.

### 2. Frontend — new page

`frontend/src/app/(receptionist)/availability/grid/page.tsx`

- Native `<table>` inside `overflow-x-auto`:
  - Sticky first column = room (`room_number — name`), links to `/rooms/{id}`.
  - One `<th>` per day-of-month showing weekday abbrev + date number; weekend
    columns get a subtle tint.
  - One `<td>` per room×day, background colored by state.
- Month navigation (prev / next, default current month) — same `currentMonth`
  state pattern as `components/room-calendar.tsx`.
- Legend row mapping color → state.
- Reachable via a toggle/link from the existing `/availability` page
  ("Month grid").

**Cell color tokens** (reuse the Tailwind families already in `RoomCalendar`):

| State        | Background           |
|--------------|----------------------|
| available    | green-100 / green-900 |
| pending      | amber-100 / amber-900 |
| confirmed    | blue-100 / blue-900   |
| checked_in   | red-100 / red-900     |
| checked_out  | slate-200 / slate-800 |
| maintenance  | slate-300 / slate-700 |

### 3. Occupied cell → popover

shadcn `Popover` (already a dependency family) anchored on the cell:

- Guest name, check-in → check-out dates, status badge.
- Actions: **View** (`/bookings/{id}`), and where the status allows:
  **Check-in** (`POST /bookings/{id}/check-in`), **Check-out**
  (`POST /bookings/{id}/check-out`), **Cancel** (`POST /bookings/{id}/cancel`).
- On any action, refetch the grid month.

The grid stores `booking_id` per occupied cell, so the popover does not need the
full booking object up front; show summary from the cell and link out for detail.

### 4. Empty cells → drag-select → new booking

- Mouse-down on an available cell starts a selection; drag highlights contiguous
  available cells **within the same room row**. Crossing an occupied cell or
  another row ends the valid range.
- Release → `check_in = first selected date`, `check_out = last selected date + 1`.
- Open `NewBookingModal` (shadcn `Dialog`) prefilled with room + dates, collecting
  `guest_name`, `guest_phone`, `num_guests`, `special_requests`.
- Submit → `POST /bookings` with the same payload shape as
  `(guest)/book/[roomId]/page.tsx` (includes a generated `idempotency_key`;
  `total_amount` is computed server-side). On success, refetch the grid.

## Components / files

- `app/services/availability_service.py` — add `get_month_grid`.
- `app/schemas/availability.py` — add `GridCell`, `RoomMonthGrid`.
- `app/api/availability.py` — add `GET /availability/grid`.
- `frontend/src/lib/types.ts` — add `RoomMonthGrid`, `GridCell` types.
- `frontend/src/app/(receptionist)/availability/grid/page.tsx` — grid page.
- `frontend/src/components/booking-popover.tsx` — occupied-cell popover.
- `frontend/src/components/new-booking-modal.tsx` — drag-select booking dialog.
- i18n keys under `availability.grid.*` and reused `calendar.*` legend keys.

## Error handling

- Backend: invalid `month` format → 422 (FastAPI query validation / explicit parse).
- Frontend: fetch failure → inline error banner (match existing availability page).
- Booking create/action failures → surface the API error message in the
  modal/popover; do not optimistically mutate the grid (refetch is the source of
  truth).
- Drag-select that includes no available cells → no-op.

## Testing

- Backend: `get_month_grid` returns occupied cells with correct state/guest, omits
  available days, marks maintenance rooms, and excludes `inactive` rooms. One test
  with a multi-night booking spanning month boundary edges.
- Frontend: render with a small fixture (matrix renders, colors map to state); a
  check that drag-select within a row produces the right check_in/check_out and
  refuses to cross an occupied cell.

## Out of scope (YAGNI)

- Length-of-stay holds (LS2/LS3/LS5).
- Grouping rows by room type / availability counts.
- Continuous span bars across nights.
- Drag-select spanning multiple rooms.
- "On request" (R) and "stop sale" (X) contract states beyond our maintenance flag.
