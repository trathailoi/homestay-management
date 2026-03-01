"""SQLAlchemy async database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Create async engine using URL from settings
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

# Session factory with expire_on_commit=False for async compatibility
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for FastAPI dependency injection."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
