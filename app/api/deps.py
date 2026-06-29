"""Shared FastAPI dependencies."""

from uuid import UUID

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.services.auth_service import AuthenticationError, AuthService


async def require_user(
    access_token: str | None = Cookie(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from the access_token cookie.

    Raises AuthenticationError (401) when the cookie is missing or invalid.
    Both admin and receptionist roles pass.
    """
    if not access_token:
        raise AuthenticationError("Not authenticated")
    service = AuthService(session)
    payload = service.decode_token(access_token)
    return await service.get_user_by_id(UUID(payload["sub"]))
