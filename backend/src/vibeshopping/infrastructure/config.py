"""Настройки приложения (pydantic-settings).

Читает переменные окружения из .env файла. Секреты (JWT_SECRET_KEY,
DATABASE_URL) никогда не должны быть захардкожены — только через .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Загружается из переменных окружения / .env."""

    DATABASE_URL: str = (
        "postgresql+asyncpg://vibeshopping:vibeshopping@localhost:5432/vibeshopping"
    )
    TEST_DATABASE_URL: str = "postgresql+asyncpg://vibeshopping:vibeshopping@localhost:5432/vibeshopping_test"

    JWT_SECRET_KEY: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
