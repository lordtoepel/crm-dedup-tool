"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Supabase
    supabase_url: str
    supabase_service_key: str  # Service role key for backend operations

    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"

    # HubSpot OAuth
    hubspot_client_id: str
    hubspot_client_secret: str
    hubspot_redirect_uri: str = "http://localhost:3000/api/hubspot/callback"

    # Encryption
    encryption_key: str  # 32-byte key for AES-256

    # App settings
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
