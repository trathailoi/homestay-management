"""Generic response envelope schemas for consistent API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(1, ge=1, description="Current page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class ErrorDetail(BaseModel):
    """Error information with machine-readable code and human-readable message."""

    code: str = Field(..., description="Machine-readable error code (e.g., 'ROOM_NOT_AVAILABLE')")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details (varies by error code)",
    )


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response envelope.

    Usage:
        response: SuccessResponse[RoomResponse] = SuccessResponse(data=room)
    """

    success: bool = True
    data: T
    meta: Meta | None = None


class ErrorResponse(BaseModel):
    """Error response envelope.

    Usage:
        return ErrorResponse(error=ErrorDetail(code='ROOM_NOT_FOUND', message='...'))
    """

    success: bool = False
    error: ErrorDetail


class ListResponse(BaseModel, Generic[T]):
    """List response envelope with pagination.

    Usage:
        response: ListResponse[RoomResponse] = ListResponse(
            data=rooms,
            meta=Meta(total=100, page=1, per_page=20)
        )
    """

    success: bool = True
    data: list[T]
    meta: Meta
