"""Протоколы репозиториев (Dependency Inversion).

Здесь домен объявляет, **какие операции** ему нужны для persistence,
но не знает, **как** они реализованы (SQLAlchemy Core, in-memory, ...).

Реализации живут в `repos/`. Use cases зависят от этих Protocol-ов,
а не от конкретных реализаций — это позволяет тестировать домен и use cases
без БД (через in-memory заглушки).

См. docs/architecture.md, раздел «Dependency Inversion».
"""

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibeshopping.domain.shopping_list import ShoppingList
from vibeshopping.domain.user import User


@runtime_checkable
class UserRepository(Protocol):
    """Репозиторий пользователей."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Найти пользователя по id. None если не найден."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Найти пользователя по email. None если не найден (FR-06)."""
        ...

    async def add(self, user: User) -> User:
        """Сохранить нового пользователя. Возвращает сохранённого."""
        ...


@runtime_checkable
class ShoppingListRepository(Protocol):
    """Репозиторий списков покупок.

    Работает с **целым агрегатом** (с items и members) — гарантируется
    консистентность в границах агрегата.
    """

    async def get_by_id(self, list_id: UUID) -> ShoppingList | None:
        """Загрузить агрегат целиком (с items и members). None если не найден."""
        ...

    async def get_all_for_user(self, user_id: UUID) -> list[ShoppingList]:
        """Все списки, в которых пользователь — владелец или участник (FR-12)."""
        ...

    async def add(self, shopping_list: ShoppingList) -> ShoppingList:
        """Сохранить новый список целиком."""
        ...

    async def update(self, shopping_list: ShoppingList) -> ShoppingList:
        """Обновить существующий список целиком (с items и members)."""
        ...

    async def delete(self, list_id: UUID) -> None:
        """Удалить список со всеми items и members (FR-14)."""
        ...
