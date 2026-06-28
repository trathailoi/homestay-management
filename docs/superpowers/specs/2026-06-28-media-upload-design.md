# Media Upload (Images + Video) — Design

Date: 2026-06-28
Status: Approved

## Goal

Let admin/receptionist users upload and delete images and videos for each room
and for the landing-page hero (plus gallery) through the receptionist portal,
replacing the current manual "drop files into `public/photos`" workflow.

## Decisions

- **Storage:** backend writes files; one shared Docker named volume serves both
  backend (write) and frontend (read). No cloud dependency.
- **Media types:** images and video together.
- **Permissions:** admin and receptionist (anyone with portal access).
- **No database:** the filesystem directory layout is the source of truth, as it
  already is for the guest landing page. No model, no migration.

## Storage Model

One named volume `homestay-media`, mounted into both services:

| Service  | Mount path           | Access | Notes                                  |
|----------|----------------------|--------|----------------------------------------|
| backend  | `/media`             | write  | env `HOMESTAY_MEDIA_ROOT=/media`       |
| frontend | `/app/public/photos` | read   | existing `photos.ts` reads it via fs   |

Directory layout (unchanged from current convention):

```
<root>/hero/                  -> hero media (first item used)
<root>/gallery/               -> gallery grid
<root>/rooms/<room_number>/   -> per-room media
```

Docker copies the image-baked contents (e.g. `placeholder.svg`) into the volume
on first creation, so placeholders survive. The volume persists across rebuilds.

## Backend

### New `app/api/media.py` (cookie-authenticated)

- `GET  /media?scope=hero|gallery|room&room_number=<n>` → list `{filename, url, type}`
- `POST /media` — multipart form: `scope`, `room_number?`, `file` → save one file
- `DELETE /media?scope=&room_number=&filename=` → delete one file

`scope=room` requires `room_number`. URLs returned as `/photos/<subdir>/<file>`
to match what the guest page already serves.

### New `app/services/media_service.py`

Pure-ish service handling the filesystem:

- `subdir_for(scope, room_number)` → resolves and validates the target subdir.
- `save(scope, room_number, upload)` → validate, sanitize filename, write bytes.
- `list_media(scope, room_number)` → return sorted `{filename, url, type}`.
- `delete(scope, room_number, filename)` → sanitize, remove.

**Validation:**
- Images: `jpg/jpeg/png/webp/avif`, ≤ 10 MB.
- Video: `mp4/webm`, ≤ 100 MB.
- Validate by extension AND content-type; reject otherwise.
- Sanitize filename: basename only, strip path separators / `..`, reject empty.
- On filename collision, append a short unique suffix.

No Pillow, no thumbnails, no transcoding, no resizing.

### Auth refactor — `app/api/deps.py`

The cookie-decode logic currently lives inline in `app/api/auth.py`'s
`get_current_user`. Extract a reusable FastAPI dependency `require_user`
(reads `access_token` cookie, decodes, 401 on missing/invalid) into
`app/api/deps.py`, and have the media endpoints depend on it. Both `admin` and
`receptionist` roles pass. (Existing room CRUD auth is out of scope.)

### Dependency

Add `python-multipart` to `pyproject.toml` (required by FastAPI for file uploads).

## Frontend

### `src/lib/photos.ts`

- Add `MEDIA_RE` covering images + video; keep `IMAGE_RE` semantics via a
  `typeOf(filename)` helper returning `'image' | 'video'`.
- Change media-returning functions to return `{ url, type }` objects:
  - `heroMedia()` → first hero item (was `heroPhoto()` string).
  - `galleryMedia()`, `roomMedia(roomNumber)`, `allRoomMedia()`.
- Placeholder stays an image.

### Components

- `Hero`: render `<video muted loop autoPlay playsInline>` when `type==='video'`,
  else `<img>`.
- Gallery and room gallery: render video items with `controls`; images as today.
- New `src/components/admin/MediaManager.tsx` (client component):
  - Props: `scope`, `roomNumber?`.
  - Lists current media (image thumb / video preview) from `GET /media`.
  - File input → raw `fetch('/api/v1/media', { method:'POST', body: FormData,
    credentials:'include' })` (not the JSON `api` client, which forces
    `Content-Type: application/json`).
  - Delete button per item → `DELETE /media?...`.
  - Refresh list after upload/delete.

### Pages

- `src/app/(receptionist)/rooms/[id]/page.tsx`: mount `<MediaManager scope="room"
  roomNumber={room.room_number} />`.
- New `src/app/(receptionist)/landing/page.tsx`: hero + gallery `MediaManager`s.

## Docker

`docker-compose.yml`:
- Add named volume `homestay-media`.
- backend: mount `homestay-media:/media`, add `HOMESTAY_MEDIA_ROOT=/media`.
- frontend: mount `homestay-media:/app/public/photos`.

## Testing

- **Backend** (`tests/`): `media_service` validation — accepts a valid image and
  a valid video, rejects a disallowed extension, rejects oversize, rejects a
  path-traversal filename.
- **Frontend** (`photos.test.ts`): extend to assert video files are classified
  `type:'video'` and images `type:'image'`, and that non-media files are ignored.

## Risks / Notes

- Frontend runs `next dev` with `force-dynamic`; runtime `public/` reads work, so
  uploads appear without a rebuild. (Confirmed against current setup.)
- First volume creation copies baked `public/photos` contents in; later image
  rebuilds do NOT overwrite the volume — intended (uploads are authoritative).

## Out of Scope (later if asked)

Media reordering UI, thumbnails/transcoding, cloud storage, DB-tracked media,
auth on existing room CRUD endpoints.
