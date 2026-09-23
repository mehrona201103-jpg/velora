"""Application configuration via environment variables."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "VELORA"
    app_env: str = "production"
    debug: bool = False
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    secret_key: str = Field(..., min_length=32)
    jwt_secret: str = Field(..., min_length=32)
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str = Field(..., description="PostgreSQL async URL")

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Admin bootstrap
    admin_email: str = "admin@velora.tj"
    admin_phone: str = "+992900000000"
    admin_password: str = "ChangeMeImmediately123!"

    # Storage
    s3_endpoint: str = ""
    s3_bucket: str = "velora-media"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "auto"
    s3_public_url: str = ""

    # Maps
    maps_provider: str = "none"
    maps_api_key: str = ""

    # AI
    ai_provider: str = "none"
    ai_api_key: str = ""
    ai_model: str = ""

    # Push
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claim_email: str = "mailto:admin@velora.tj"
    fcm_project_id: str = ""
    fcm_credentials_json: str = ""

    # Business
    default_delivery_fee: str = "15.00"
    currency: str = "TJS"
    pickup_reservation_days: int = 5
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @field_validator("database_url")
    @classmethod
    def ensure_async_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
