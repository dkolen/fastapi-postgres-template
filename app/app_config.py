"""Application configuration.

Values are read from environment variables (and a local `.env` file, if present)
and validated once at import time. Anywhere in the app:

    from app.app_config import config

    config.POSTGRES_HOST
"""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "fastapi-postgres-template"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"

    # Postgres
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    DB_CONNECT_RETRIES: int = 5
    DB_CONNECT_RETRY_DELAY_SECONDS: float = 2.0

    @computed_field
    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()


config = get_config()
