# View Biển Guest Landing — Design

**Date:** 2026-06-28
**Domain:** `viewbien.ninhvanland.com` (subdomain of the village-wide `ninhvanland.com`)
**Goal:** A visitor-facing landing page for the single homestay "Nhà nghỉ View Biển" that lets guests view the place, browse rooms, and book — applying the Stitch "Horizon Bound" design system.

## Context

- Backend (FastAPI) already implements rooms, availability, and booking. Guest-relevant endpoints are public (no auth):
  - `GET /rooms?status=active` — list rooms (`Room`: id, room_number, room_type, name, description, max_occupancy, base_price_per_night, amenities[], status).
  - `GET /availability?check_in&check_out&guests` — available rooms for a date range (`AvailableRoom`: + total_price).
  - `POST /bookings` — create booking (unchanged).
- Frontend (Next.js 16, React 19, Tailwind v4, shadcn, radix-ui, next-themes, react-day-picker, sonner). i18n is a custom context with `vi.json`/`en.json`, Vietnamese default; dark/light via next-themes already wired.
- Current `(guest)/page.tsx` is a bare search-form-first list — no photos, no story. This replaces it.
- Multi-listing `ninhvanland.com` is **out of scope**; this is single-homestay only.

## Scope

In: full single-page scroll landing (hero + gallery, rooms + booking, location + reviews) and a light restyle of the existing `/book/[roomId]` flow to match.
Out: about/story section, multi-homestay listing, CMS, automated Google photo/review scraping.

## Design tokens — Horizon Bound

Add the Horizon Bound system to `globals.css` as CSS variables + Tailwind v4 `@theme`:

- Fonts via `next/font/google`: **Hanken Grotesk** (headlines/display/price), **Inter** (body/labels/UI).
- Primary CTA = Coral `#ff385c` (white text) — reserved for "Đặt phòng" / "Request booking".
- Secondary/nav = Action Blue `#003580`.
- Surfaces near-white (`#faf9fb` bg, `#ffffff` cards). Radius: 8px controls, 16px cards, full for chips/pills.
- Soft ambient shadows (no heavy borders); 1px `#EBEBEB` outline only where white-on-white needs separation.
- Dark mode: keep the existing toggle; retint the `.dark` vars to the blue/coral family (light remains the primary, designed-for mode).

## Sections (single page, anchor nav)

1. **Hero** — full-bleed sea-view photo, "Nhà nghỉ View Biển" heading + tagline, Coral CTA scrolling to the rooms section. Reuses the sticky pill header (language + theme toggles).
2. **Gallery** — responsive photo grid; tap opens a lightbox (radix `Dialog`, already installed).
3. **Rooms + booking** — single section with two states:
   - *Browse* (default): `GET /rooms?status=active`, one card per room (photo, name, type badge, description, amenities chips, price/night).
   - *Availability*: a date + guests bar runs `GET /availability`; results replace the browse list (total price + "Request booking" → `/book/[roomId]?check_in&check_out&guests`).
4. **Location + reviews** — Google Maps embed iframe (place URL, no API key) + address + getting-there note. Below it, 3–4 hand-picked Google review quotes from static `lib/reviews.ts` (kept in original Vietnamese, star rating + reviewer name + Google attribution) and a link to full Google reviews.

## Photos

- Directory convention: `frontend/public/photos/hero/`, `.../gallery/`, `.../rooms/<room_number>/`.
- `frontend/src/lib/photos.ts`: `heroPhoto()`, `galleryPhotos()`, `roomPhotos(roomNumber)` — return file paths, fall back to a bundled placeholder when a directory is empty/missing.
- Built with placeholders; the owner drops real files (downloaded from Google Maps reviews) into the folders later — **no code change** required.

## Data flow

- Landing is a client component: `GET /rooms` on mount → browse cards; date search → `GET /availability` → results state; "Request booking" routes to existing booking page; `POST /bookings` unchanged.

## Error handling

- Rooms/availability fetch failure → friendly retry card (reuse existing red-card pattern + i18n string).
- Missing photo → placeholder from `photos.ts`.
- Map iframe is static (no failure path).

## i18n

- Add landing keys to `vi.json` / `en.json` (hero tagline, section titles, gallery/empty states, reviews label, location/getting-there).
- Review quote text stored as-is in `reviews.ts` (original Vietnamese); not machine-translated.

## Files

**New**
- `frontend/src/app/(guest)/page.tsx` — rewrite to compose the landing sections.
- `frontend/src/components/guest/hero.tsx`
- `frontend/src/components/guest/gallery.tsx`
- `frontend/src/components/guest/rooms-booking.tsx` (stateful browse/availability + booking handoff)
- `frontend/src/components/guest/location-reviews.tsx`
- `frontend/src/lib/photos.ts`
- `frontend/src/lib/reviews.ts` (static review data)
- `frontend/public/photos/**` + a placeholder asset.

**Modify**
- `frontend/src/app/globals.css` — Horizon Bound tokens.
- root layout — Hanken Grotesk + Inter via `next/font`.
- `frontend/src/app/(guest)/layout.tsx` — allow full-bleed (drop the `max-w-4xl` clamp; keep header/footer).
- `frontend/src/components/guest-header.tsx` — restyle to Horizon Bound pill.
- `frontend/src/i18n/vi.json`, `frontend/src/i18n/en.json` — new keys (i18n consumed via `src/lib/language-context.tsx`).
- `frontend/src/app/(guest)/book/[roomId]/page.tsx` — light restyle to match.

## Testing

- Gate: `eslint` + `next build` pass.
- One unit test on `photos.ts` (mapping + placeholder fallback — the only non-trivial logic).
- Visual verification of the running landing via the run/verify flow.

## Out of scope / later

- Multi-homestay listing on `ninhvanland.com`.
- Real Google photo/review ingestion (manual drop for now).
- Subdomain DNS/deploy wiring (Cloudflare) — infra, not this codebase change.
