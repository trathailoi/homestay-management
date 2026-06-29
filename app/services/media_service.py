"""Filesystem-backed media storage for room/hero/gallery images and video.

No database: the directory layout under ``settings.media_root`` is the source of
truth (the frontend reads the same dir mounted at ``public/photos``)::

    <root>/hero/
    <root>/gallery/
    <root>/rooms/<room_number>/
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from app.config import settings
from app.exceptions import MediaNotFoundError, MediaValidationError

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "avif"}
VIDEO_EXTS = {"mp4", "webm"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024

_SCOPES = {"hero", "gallery", "room"}
# room_number is also a DB column (String(20)); allow only safe path-segment chars.
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9 ._-]{1,40}$")


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def media_type(filename: str) -> str | None:
    """Return ``"image"``/``"video"`` for a known extension, else ``None``."""
    ext = _ext(filename)
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def _sanitize_segment(value: str) -> str:
    """Validate a single path segment (room_number); reject traversal."""
    value = value.strip()
    if ".." in value or not _SAFE_SEGMENT.match(value):
        raise MediaValidationError(
            f"Invalid path segment: {value!r}", details={"value": value}
        )
    return value


def _sanitize_filename(filename: str) -> str:
    """Strip any directory components and reject empty/hidden names."""
    name = Path(filename).name  # drops dirs and '..' components
    if not name or name.startswith("."):
        raise MediaValidationError(
            f"Invalid filename: {filename!r}", details={"filename": filename}
        )
    return name


class MediaService:
    """Read/write media files under the configured media root."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.media_root)

    def subdir_for(self, scope: str, room_number: str | None) -> str:
        if scope not in _SCOPES:
            raise MediaValidationError(
                f"Unknown scope: {scope!r}", details={"scope": scope}
            )
        if scope == "room":
            if not room_number:
                raise MediaValidationError("room_number is required for scope=room")
            return f"rooms/{_sanitize_segment(room_number)}"
        return scope

    def _dir(self, scope: str, room_number: str | None) -> Path:
        return self.root / self.subdir_for(scope, room_number)

    def _item(self, subdir: str, filename: str) -> dict:
        return {
            "filename": filename,
            "url": f"/photos/{subdir}/{filename}",
            "type": media_type(filename),
        }

    def save(
        self,
        scope: str,
        room_number: str | None,
        filename: str,
        data: bytes,
        content_type: str | None = None,
    ) -> dict:
        mtype = media_type(filename)
        if mtype is None:
            raise MediaValidationError(
                f"Unsupported file type: {filename!r}",
                details={"allowed": sorted(IMAGE_EXTS | VIDEO_EXTS)},
            )
        # Validate content-type against the extension's category when provided.
        if content_type and not content_type.startswith(f"{mtype}/"):
            raise MediaValidationError(
                f"Content-type {content_type!r} does not match a {mtype} file",
                details={"content_type": content_type, "expected": f"{mtype}/*"},
            )
        limit = MAX_IMAGE_BYTES if mtype == "image" else MAX_VIDEO_BYTES
        if len(data) > limit:
            raise MediaValidationError(
                f"File exceeds {limit // (1024 * 1024)}MB limit for {mtype}",
                details={"size": len(data), "limit": limit},
            )

        subdir = self.subdir_for(scope, room_number)
        dest_dir = self.root / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)

        name = _sanitize_filename(filename)
        path = dest_dir / name
        if path.exists():  # avoid clobbering an existing file
            stem, ext = name.rsplit(".", 1)
            name = f"{stem}-{secrets.token_hex(3)}.{ext}"
            path = dest_dir / name
        path.write_bytes(data)
        return self._item(subdir, name)

    def list_media(self, scope: str, room_number: str | None) -> list[dict]:
        subdir = self.subdir_for(scope, room_number)
        dest_dir = self.root / subdir
        if not dest_dir.is_dir():
            return []
        names = sorted(
            f.name
            for f in dest_dir.iterdir()
            if f.is_file() and media_type(f.name) is not None
        )
        return [self._item(subdir, n) for n in names]

    def delete(self, scope: str, room_number: str | None, filename: str) -> None:
        subdir = self.subdir_for(scope, room_number)
        name = _sanitize_filename(filename)
        path = self.root / subdir / name
        if not path.is_file():
            raise MediaNotFoundError(filename)
        path.unlink()
