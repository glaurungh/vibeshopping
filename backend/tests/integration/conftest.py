"""Конфигест для интеграционных тестов.

Каждый тест получает свежий engine + чистую БД.
Требует запущенный PostgreSQL (docker-compose up -d).
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vibeshopping.infrastructure.config import Settings
from vibeshopping.infrastructure.tables import metadata

settings = Settings()


@pytest.fixture
async def db_session() -> AsyncSession:
    """Сессия с реальной PostgreSQL. Таблицы создаются/удаляются."""
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False, pool_size=1)

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)

    await engine.dispose()
