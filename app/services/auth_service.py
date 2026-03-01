"""Authentication service for user management and JWT tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import HomestayError
from app.models.user import User


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt with default work factor."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class AuthenticationError(HomestayError):
    """Raised on authentication failures.

    Used for:
    - Invalid credentials (wrong username or password)
    - Expired JWT tokens
    - Invalid/malformed JWT tokens
    - Missing authentication

    Note: Same error raised whether username doesn't exist or password is wrong
    to prevent username enumeration attacks.
    """

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthService:
    """Handles user authentication and JWT token lifecycle.

    Methods follow the same session-based pattern as RoomService/BookingService.
    The session is injected via dependency injection in route handlers.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self, username: str, password: str, role: str = "receptionist"
    ) -> User:
        """Create a new user account.

        Args:
            username: Unique username (max 100 chars)
            password: Plain text password (will be hashed)
            role: User role (default "receptionist")

        Returns:
            Created User instance

        Raises:
            HomestayError: If username already exists (code: USERNAME_EXISTS)
        """
        # Check for existing username
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise HomestayError(
                message=f"Username '{username}' already exists",
                code="USERNAME_EXISTS",
            )

        # Create user with hashed password
        user = User(
            username=username,
            password_hash=_hash_password(password),
            role=role,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, username: str, password: str) -> User:
        """Verify credentials and return user.

        Args:
            username: Username to authenticate
            password: Plain text password to verify

        Returns:
            Authenticated User instance

        Raises:
            AuthenticationError: If credentials are invalid
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        # Timing-safe comparison: bcrypt.checkpw handles this internally
        # We use the same error whether user not found or password wrong
        if not user or not _verify_password(password, user.password_hash):
            raise AuthenticationError()

        return user

    @staticmethod
    def create_token(user_id: UUID, role: str) -> str:
        """Create a JWT access token.

        Args:
            user_id: User UUID to encode in token
            role: User role to encode in token

        Returns:
            Encoded JWT token string
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "role": role,
            "exp": expire,
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded payload dict with 'sub', 'role', 'exp' keys

        Raises:
            AuthenticationError: If token is expired or invalid
        """
        try:
            return jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Get user by ID.

        Args:
            user_id: User UUID to look up

        Returns:
            User instance

        Raises:
            AuthenticationError: If user not found
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError("User not found")
        return user
