from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "VELORA"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./velora.db"
    SECRET_KEY: str = "dev-secret-change-in-production-please-make-it-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    PORT: int = 8000

    FIRST_OWNER_EMAIL: str = "owner@velora.tj"
    FIRST_OWNER_PASSWORD: str = "ChangeThisStrongPassword123!"
    # aliases used in .env.example / Railway
    OWNER_EMAIL: str | None = None
    OWNER_PASSWORD: str | None = None
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    # e.g. https://velora.up.railway.app
    PUBLIC_BASE_URL: str = "https://velora.up.railway.app"
    # approx TJS per 1 loyalty point
    LOYALTY_POINTS_PER_100_TJS: float = 1.0

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
