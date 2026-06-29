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

    # Media uploads: shared-volume root (frontend reads the same dir at public/photos)
    media_root: str = "/media"

    # JWT Authentication
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours - typical receptionist shift

    # Booking agent (OpenAI-compatible: OpenAI, ZAI GLM, ...)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    agent_model: str = "gpt-4o-mini"
    # Comma-separated Zalo chat ids allowed to use the agent (empty = none, fail closed).
    # Approved staff are added at runtime via admin /approve; this is the static seed.
    agent_allowed_senders: str = ""
    # Comma-separated admin chat ids: always allowed + can /approve others (env-only).
    agent_admins: str = ""

    # Zalo Bot Platform (https://bot.zaloplatforms.com) — static token, no refresh
    zalo_bot_token: str = ""  # bot token from the Bot Platform console (polling via getUpdates)


settings = Settings()
