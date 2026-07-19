"""Реализация UserRepository на SQLAlchemy Core.

Маппинг строки БД → доменная модель User — вручную. См.
docs/architecture.md, раздел «SQLAlchemy Core, а не ORM».
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibeshopping.domain.user import User
from vibeshopping.infrastructure.tables import users


class SqlAlchemyUserRepository:
    """Реализация UserRepository на SQLAlchemy Core + asyncpg."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(users).where(users.c.id == user_id)
        row = (await self._session.execute(stmt)).first()
        return _row_to_user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(users).where(users.c.email == email.lower())
        row = (await self._session.execute(stmt)).first()
        return _row_to_user(row) if row else None

    async def add(self, user: User) -> User:
        await self._session.execute(
            users.insert().values(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                created_at=user.created_at,
            )
        )
        await self._session.commit()
        return user


def _row_to_user(row: Any) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        created_at=row.created_at,
    )
