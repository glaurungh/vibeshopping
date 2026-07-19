"""Use cases управления списками покупок.

Каждый use case загружает агрегат через репозиторий, выполняет операцию
(часто — вызывает метод корня, который сам защищает инварианты), и сохраняет
результат. Если список не существует — поднимает ListNotFoundError.

Покрытые требования (см. docs/spec.md):
    - FR-10: создание списка
    - FR-11: при создании пользователь становится владельцем
    - FR-12: пользователь видит только свои списки
    - FR-13: только владелец может переименовать/удалить
    - FR-14: при удалении список исчезает со всем содержимым
"""

from uuid import UUID

from vibeshopping.domain.errors import ListNotFoundError, NotListOwnerError
from vibeshopping.domain.repositories import ShoppingListRepository
from vibeshopping.domain.shopping_list import ShoppingList


class _ListUseCase:
    """Базовый класс для use cases, работающих с одним списком.

    Предоставляет общую логику загрузки агрегата с проверкой существования
    (поднимает ListNotFoundError, если список не найден).
    """

    def __init__(self, repo: ShoppingListRepository) -> None:
        self._repo = repo

    async def _load_existing(self, list_id: UUID) -> ShoppingList:
        lst = await self._repo.get_by_id(list_id)
        if lst is None:
            raise ListNotFoundError(list_id)
        return lst


class CreateList:
    """Создать список покупок (FR-10, FR-11)."""

    def __init__(self, repo: ShoppingListRepository) -> None:
        self._repo = repo

    async def execute(self, name: str, owner_id: UUID) -> ShoppingList:
        shopping_list = ShoppingList.create(name=name, owner_id=owner_id)
        return await self._repo.add(shopping_list)


class GetLists:
    """Все списки пользователя (как владельца или участника) (FR-12)."""

    def __init__(self, repo: ShoppingListRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: UUID) -> list[ShoppingList]:
        return await self._repo.get_all_for_user(user_id)


class GetList(_ListUseCase):
    """Получить один список. Только участники (FR-12)."""

    async def execute(self, list_id: UUID, actor_id: UUID) -> ShoppingList:
        lst = await self._load_existing(list_id)
        if not lst.is_member(actor_id):
            # Не выдаём, что список существует, не-участникам
            # (object-level authorization).
            raise ListNotFoundError(list_id)
        return lst


class RenameList(_ListUseCase):
    """Переименовать список. Только владелец (FR-13)."""

    async def execute(
        self, list_id: UUID, new_name: str, actor_id: UUID
    ) -> ShoppingList:
        lst = await self._load_existing(list_id)
        lst.rename(new_name=new_name, actor_id=actor_id)  # поднимёт NotListOwnerError
        return await self._repo.update(lst)


class DeleteList(_ListUseCase):
    """Удалить список. Только владелец (FR-13, FR-14)."""

    async def execute(self, list_id: UUID, actor_id: UUID) -> None:
        lst = await self._load_existing(list_id)
        # Сначала проверяем членство, чтобы не выдавать существование списка
        # не-участникам; затем — владение.
        if not lst.is_member(actor_id):
            raise ListNotFoundError(list_id)
        if not lst.is_owner(actor_id):
            raise NotListOwnerError(list_id, actor_id)
        await self._repo.delete(list_id)
