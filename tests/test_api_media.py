"""Tests for the media upload API endpoints (auth + multipart)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.auth_service import AuthService

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture(autouse=True)
def media_root(tmp_path, monkeypatch):
    """Point MediaService at a temp dir for the duration of each test."""
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    return tmp_path


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, session: AsyncSession) -> AsyncClient:
    """A client carrying a valid auth cookie."""
    await AuthService(session).register("recep", "password123", "receptionist")
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "recep", "password": "password123"}
    )
    assert resp.status_code == 200
    return client


@pytest.mark.asyncio
async def test_upload_list_delete_cycle(auth_client: AsyncClient) -> None:
    up = await auth_client.post(
        "/api/v1/media",
        data={"scope": "hero"},
        files={"file": ("shot.png", PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    item = up.json()["data"]
    assert item["type"] == "image"
    assert item["url"].startswith("/photos/hero/")

    listed = await auth_client.get("/api/v1/media", params={"scope": "hero"})
    assert listed.status_code == 200
    assert [i["filename"] for i in listed.json()["data"]] == [item["filename"]]

    deleted = await auth_client.delete(
        "/api/v1/media", params={"scope": "hero", "filename": item["filename"]}
    )
    assert deleted.status_code == 200
    after = await auth_client.get("/api/v1/media", params={"scope": "hero"})
    assert after.json()["data"] == []


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/media",
        data={"scope": "hero"},
        files={"file": ("shot.png", PNG, "image/png")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reject_bad_extension(auth_client: AsyncClient) -> None:
    resp = await auth_client.post(
        "/api/v1/media",
        data={"scope": "gallery"},
        files={"file": ("evil.txt", b"nope", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MEDIA_VALIDATION"


@pytest.mark.asyncio
async def test_delete_missing_returns_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.delete(
        "/api/v1/media", params={"scope": "hero", "filename": "ghost.png"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "MEDIA_NOT_FOUND"
