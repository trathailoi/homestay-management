"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="HOMESTAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database URLs
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/homestay"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/homestay"

    # Availability configuration
    availability_window_days: int = 365

    # JWT Authentication
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours - typical receptionist shift


settings = Settings()
