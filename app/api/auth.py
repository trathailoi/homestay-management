"""Authentication API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthenticationError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[TokenResponse]:
    """Login and receive JWT token.

    The token is returned both in the response body (for API clients)
    and set as an httpOnly cookie (for browser sessions).
    """
    service = AuthService(session)
    user = await service.authenticate(data.username, data.password)
    token = service.create_token(user.id, user.role)

    # Set httpOnly cookie for browser sessions
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
    """Clear authentication cookie."""
    response.delete_cookie(key="access_token")
    return SuccessResponse(data={"message": "Logged out successfully"})


@router.get("/me")
async def get_current_user(
    access_token: str | None = Cookie(None),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UserResponse]:
    """Get currently authenticated user.

    Reads JWT from httpOnly cookie and returns user info.
    """
    if not access_token:
        raise AuthenticationError("Not authenticated")

    service = AuthService(session)
    payload = service.decode_token(access_token)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.post("/register")
async def register(
    data: RegisterRequest,
    access_token: str | None = Cookie(None),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UserResponse]:
    """Register a new user account.

    SECURITY: Requires authentication. The first admin user must be
    created via the seed script. All subsequent users are created
    through this authenticated endpoint.

    For MVP, any authenticated user can create new users.
    Future: restrict to admin-role users only.
    """
    # Require authentication to create new users
    if not access_token:
        raise AuthenticationError("Authentication required to register users")

    service = AuthService(session)

    # Verify the caller is authenticated
    service.decode_token(access_token)

    # Create the new user
    user = await service.register(data.username, data.password, data.role)
    return SuccessResponse(data=UserResponse.model_validate(user))
