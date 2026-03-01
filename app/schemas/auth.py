"""Pydantic schemas for authentication API endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for login (POST /auth/login)."""

    username: Annotated[str, Field(max_length=100)]
    password: Annotated[str, Field(max_length=200)]


class RegisterRequest(BaseModel):
    """Request body for user registration (POST /auth/register).

    Note: Password has minimum length validation (6 chars).
    Registration requires authentication in production.
    """

    username: Annotated[str, Field(max_length=100)]
    password: Annotated[str, Field(min_length=6, max_length=200)]
    role: str = "receptionist"


class TokenResponse(BaseModel):
    """Response body for successful login.

    The access_token is also set as an httpOnly cookie by the route handler.
    Body token enables API-only clients (curl, MCP server).
    Cookie enables browser-based sessions.
    """

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response body for user endpoints."""

    model_config = {"from_attributes": True}

    id: UUID
    username: str
    role: str
    created_at: datetime
