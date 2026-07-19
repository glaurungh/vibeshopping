"""Интеграционные тесты SqlAlchemyUserRepository.

Требуют запущенный PostgreSQL (docker-compose up -d). Фикстура db_session
создаёт/удаляет таблицы перед/после каждого теста (conftest.py).
"""

from uuid import uuid4

from sqlalchemy import select

from vibeshopping.domain.user import User
from vibeshopping.infrastructure.tables import users
from vibeshopping.repos.user_repository import SqlAlchemyUserRepository


class TestUserRepository:
    async def test_add_persists_user(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        user = User(
            email="alice@example.com",
            hashed_password="hashed-secret",
        )

        result = await repo.add(user)

        assert result.id == user.id
        assert result.email == user.email
        # Проверяем через прямой SQL-запрос к БД
        stmt = select(users).where(users.c.id == user.id)
        row = (await db_session.execute(stmt)).first()
        assert row is not None
        assert row.email == "alice@example.com"

    async def test_get_by_id_returns_user(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        user = await repo.add(User(email="bob@example.com", hashed_password="hash"))

        result = await repo.get_by_id(user.id)

        assert result is not None
        assert result.email == "bob@example.com"
        assert result.hashed_password == "hash"

    async def test_get_by_id_returns_none_for_unknown(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)

        result = await repo.get_by_id(uuid4())

        assert result is None

    async def test_get_by_email_returns_user(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        await repo.add(User(email="carol@example.com", hashed_password="hash"))

        result = await repo.get_by_email("carol@example.com")

        assert result is not None
        assert result.email == "carol@example.com"

    async def test_get_by_email_returns_none_for_unknown(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)

        result = await repo.get_by_email("ghost@example.com")

        assert result is None

    async def test_get_by_email_is_case_insensitive(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        await repo.add(User(email="dave@example.com", hashed_password="hash"))

        result = await repo.get_by_email("DAVE@example.com")

        assert result is not None
        assert result.email == "dave@example.com"

    async def test_add_preserves_timestamps(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        before_save = User(
            email="eve@example.com",
            hashed_password="hash",
        )

        result = await repo.add(before_save)

        # created_at должен совпадать между доменной моделью и БД
        assert result.created_at is not None
        loaded = await repo.get_by_id(result.id)
        assert loaded is not None
        assert loaded.created_at == result.created_at

    async def test_get_returns_user_with_all_fields(self, db_session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        original = User(
            email="frank@example.com",
            hashed_password="my-hash",
        )
        saved = await repo.add(original)

        result = await repo.get_by_id(saved.id)

        assert result is not None
        assert result.id == saved.id
        assert result.email == "frank@example.com"
        assert result.hashed_password == "my-hash"
        assert result.created_at == saved.created_at
