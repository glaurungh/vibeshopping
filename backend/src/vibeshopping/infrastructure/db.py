"""Async database engine и session factory.

Предоставляет:
- create_engine() — для основного приложения.
- create_test_engine() — для интеграционных тестов (отдельная БД).
- get_session() — async generator, для использования как FastAPI Depends.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vibeshopping.infrastructure.config import Settings

settings = Settings()


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Создать async engine для PostgreSQL."""
    url = database_url or settings.DATABASE_URL
    return create_async_engine(url, echo=False)


def create_test_engine() -> AsyncEngine:
    """Создать async engine для тестовой БД."""
    return create_async_engine(settings.TEST_DATABASE_URL, echo=False)


def _create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


# --- Production session factory ---
_engine = create_engine()
_session_factory = _create_session_factory(_engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async generator для FastAPI Depends. Выдаёт одну сессию на запрос."""
    async with _session_factory() as session:
        yield session
