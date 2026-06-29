"""Tests for MediaService filesystem storage + validation."""

import pytest

from app.exceptions import MediaNotFoundError, MediaValidationError
from app.services.media_service import (
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    MediaService,
    media_type,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"0" * 32


@pytest.fixture
def svc(tmp_path):
    return MediaService(root=str(tmp_path))


def test_media_type_classification():
    assert media_type("a.JPG") == "image"
    assert media_type("a.webp") == "image"
    assert media_type("clip.mp4") == "video"
    assert media_type("clip.webm") == "video"
    assert media_type("notes.txt") is None
    assert media_type("noext") is None


def test_save_image(svc):
    item = svc.save("hero", None, "shot.png", PNG, "image/png")
    assert item["type"] == "image"
    assert item["url"] == f"/photos/hero/{item['filename']}"
    assert svc.list_media("hero", None) == [item]


def test_save_video_to_room(svc):
    item = svc.save("room", "101", "tour.mp4", MP4, "video/mp4")
    assert item["type"] == "video"
    assert item["url"].startswith("/photos/rooms/101/")


def test_reject_disallowed_extension(svc):
    with pytest.raises(MediaValidationError):
        svc.save("gallery", None, "evil.txt", b"hi", "text/plain")


def test_reject_content_type_mismatch(svc):
    with pytest.raises(MediaValidationError):
        svc.save("hero", None, "shot.png", PNG, "video/mp4")


def test_reject_oversize(svc):
    big = b"0" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(MediaValidationError):
        svc.save("hero", None, "shot.png", big, "image/png")
    # video limit is higher than the image limit
    assert MAX_VIDEO_BYTES > MAX_IMAGE_BYTES


def test_path_traversal_filename_is_contained(svc, tmp_path):
    item = svc.save("hero", None, "../../etc/passwd.png", PNG, "image/png")
    assert "/" not in item["filename"]
    # file landed inside the hero dir, not outside the root
    assert (tmp_path / "hero" / item["filename"]).is_file()


def test_path_traversal_room_number_rejected(svc):
    with pytest.raises(MediaValidationError):
        svc.save("room", "../../etc", "shot.png", PNG, "image/png")


def test_room_scope_requires_room_number(svc):
    with pytest.raises(MediaValidationError):
        svc.save("room", None, "shot.png", PNG, "image/png")


def test_collision_keeps_both(svc):
    a = svc.save("gallery", None, "a.png", PNG, "image/png")
    b = svc.save("gallery", None, "a.png", PNG, "image/png")
    assert a["filename"] != b["filename"]
    assert len(svc.list_media("gallery", None)) == 2


def test_list_empty_dir(svc):
    assert svc.list_media("gallery", None) == []


def test_delete(svc):
    item = svc.save("hero", None, "shot.png", PNG, "image/png")
    svc.delete("hero", None, item["filename"])
    assert svc.list_media("hero", None) == []
    with pytest.raises(MediaNotFoundError):
        svc.delete("hero", None, item["filename"])
