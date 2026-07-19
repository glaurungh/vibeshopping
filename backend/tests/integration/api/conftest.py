"""Конфигест для API интеграционных тестов.

Предоставляет `api_client` — httpx.AsyncClient с реальной БД (per-test)
и overridden get_session dependency.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vibeshopping.infrastructure.config import Settings
from vibeshopping.infrastructure.tables import metadata
from vibeshopping.main import app
from vibeshopping.views.dependencies import get_session

settings = Settings()


@pytest.fixture
async def api_client():
    """httpx.AsyncClient с реальной БД. Таблицы создаются/удаляются per-test."""
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False, pool_size=1)

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncSession:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)

    await engine.dispose()
