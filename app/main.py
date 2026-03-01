"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.availability import router as availability_router
from app.api.bookings import router as bookings_router
from app.api.rooms import router as rooms_router
from app.database import SessionLocal
from app.exceptions import (
    BookingNotFoundError,
    BookingValidationError,
    InvalidStatusTransitionError,
    RoomNotAvailableError,
    RoomNotFoundError,
)

app = FastAPI(
    title="Homestay Management API",
    description="Room inventory, availability, and booking management for homestays",
    version="0.1.0",
)

# Include routers
app.include_router(rooms_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")


# Global exception handlers
@app.exception_handler(RoomNotFoundError)
async def room_not_found_handler(request: Request, exc: RoomNotFoundError) -> JSONResponse:
    """Handle room not found errors -> 404."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(BookingNotFoundError)
async def booking_not_found_handler(
    request: Request, exc: BookingNotFoundError
) -> JSONResponse:
    """Handle booking not found errors -> 404."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(RoomNotAvailableError)
async def room_not_available_handler(
    request: Request, exc: RoomNotAvailableError
) -> JSONResponse:
    """Handle room not available errors -> 409 Conflict."""
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(InvalidStatusTransitionError)
async def invalid_transition_handler(
    request: Request, exc: InvalidStatusTransitionError
) -> JSONResponse:
    """Handle invalid status transition errors -> 400."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(BookingValidationError)
async def booking_validation_handler(
    request: Request, exc: BookingValidationError
) -> JSONResponse:
    """Handle booking validation errors -> 400."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.get("/api/v1/health")
async def health_check() -> dict:
    """Health check endpoint that verifies database connectivity."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {
            "success": True,
            "data": {"status": "healthy"},
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Database connection failed",
                    "details": {},
                },
            },
        )
