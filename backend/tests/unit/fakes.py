"""In-memory фейки протоколов репозиториев и портов для unit-тестов.

В Clean Architecture unit-тесты use cases не должны зависеть от БД или
реальных крипто-библиотек. Здесь — тривиальные реализации интерфейсов
из `domain/repositories.py` и `services/ports.py`, которые хранят данные
в памяти и работают мгновенно.

Этот файл — вспомогательный код тестов, не часть приложения.
"""

from collections.abc import Iterable
from uuid import UUID, uuid4

from vibeshopping.domain.shopping_list import ShoppingList
from vibeshopping.domain.user import User


class InMemoryUserRepository:
    """Реализация UserRepository на словаре. Ключ — email (нижний регистр)."""

    def __init__(self, initial: Iterable[User] = ()) -> None:
        self._by_id: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}
        for u in initial:
            self._store(u)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email.lower())

    async def add(self, user: User) -> User:
        self._store(user)
        return user

    def _store(self, user: User) -> None:
        self._by_id[user.id] = user
        self._by_email[user.email.lower()] = user


class InMemoryShoppingListRepository:
    """Реализация ShoppingListRepository на словаре."""

    def __init__(self, initial: Iterable[ShoppingList] = ()) -> None:
        self._by_id: dict[UUID, ShoppingList] = {lst.id: lst for lst in initial}

    async def get_by_id(self, list_id: UUID) -> ShoppingList | None:
        return self._by_id.get(list_id)

    async def get_all_for_user(self, user_id: UUID) -> list[ShoppingList]:
        return [
            lst
            for lst in self._by_id.values()
            if any(m.user_id == user_id for m in lst.members)
        ]

    async def add(self, shopping_list: ShoppingList) -> ShoppingList:
        self._by_id[shopping_list.id] = shopping_list
        return shopping_list

    async def update(self, shopping_list: ShoppingList) -> ShoppingList:
        self._by_id[shopping_list.id] = shopping_list
        return shopping_list

    async def delete(self, list_id: UUID) -> None:
        self._by_id.pop(list_id, None)


class FakePasswordHasher:
    """Тривиальный хешер для тестов. НЕ использовать в продакшене.

    Использует SHA-256 с фиксированной солью — этого достаточно, чтобы
    пароль НЕ восстанавливался из хеша (инвариант FR-02), что важно
    для осмысленности тестов use cases.
    """

    _SALT = "vibeshopping-test-salt"

    def hash(self, password: str) -> str:
        import hashlib

        digest = hashlib.sha256((self._SALT + password).encode()).hexdigest()
        return f"fake${digest}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == self.hash(password)


class FakeTokenService:
    """Токены хранятся в памяти. user_id кодируется как строка."""

    def __init__(self) -> None:
        # token -> user_id
        self._tokens: dict[str, UUID] = {}

    def create_access_token(self, user_id: UUID) -> str:
        token = f"access-{user_id}-{uuid4()}"
        self._tokens[token] = user_id
        return token

    def create_refresh_token(self, user_id: UUID) -> str:
        token = f"refresh-{user_id}-{uuid4()}"
        self._tokens[token] = user_id
        return token

    def decode_user_id(self, token: str) -> UUID | None:
        return self._tokens.get(token)

    def invalidate(self, token: str) -> None:
        """Утилита для тестов: отозвать токен."""
        self._tokens.pop(token, None)
