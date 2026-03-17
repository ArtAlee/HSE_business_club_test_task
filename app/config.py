from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HSE Business Club Backend"
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+psycopg2://app:app@db:5432/hse_business_club",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    telegram_bot_token: str = Field(default="telegram-bot-token", alias="TELEGRAM_BOT_TOKEN")
    telegram_auth_max_age_seconds: int = 300
    qr_ttl_seconds: int = Field(default=120, alias="QR_TTL_SECONDS")
    admin_token: str = Field(default="admin-token", alias="ADMIN_TOKEN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
