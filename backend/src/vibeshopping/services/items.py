"""Use cases управления элементами списка.

Все операции требуют членства в списке (владелец или участник, FR-21..25).
Инварианты защищены в агрегате; здесь — оркестрация: загрузка, вызов,
сохранение. Внешнему пользователю возвращаем ListNotFoundError (не
раскрываем существование списка — object-level authorization).
"""

from uuid import UUID

from vibeshopping.domain.errors import ListNotFoundError
from vibeshopping.domain.repositories import ShoppingListRepository
from vibeshopping.domain.shopping_list import ListItem, ShoppingList


class _ItemListUseCase:
    """Базовый класс с общей логикой загрузки и проверки членства.

    Идентификатор list_id должен быть валидным, а actor — участником списка;
    иначе ListNotFoundError. Подклассы вызывают свои методы агрегата.
    """

    def __init__(self, repo: ShoppingListRepository) -> None:
        self._repo = repo

    async def _load_for_actor(self, list_id: UUID, actor_id: UUID) -> ShoppingList:
        lst = await self._repo.get_by_id(list_id)
        if lst is None or not lst.is_member(actor_id):
            raise ListNotFoundError(list_id)
        return lst


class AddItem(_ItemListUseCase):
    """Добавить товар в список (FR-20)."""

    async def execute(
        self,
        list_id: UUID,
        name: str,
        actor_id: UUID,
        quantity: str | None = None,
    ) -> ListItem:
        lst = await self._load_for_actor(list_id, actor_id)
        item = lst.add_item(name=name, actor_id=actor_id, quantity=quantity)
        await self._repo.update(lst)
        return item


class UpdateItem(_ItemListUseCase):
    """Редактировать товар (FR-22). None = «оставить как есть»."""

    async def execute(
        self,
        list_id: UUID,
        item_id: UUID,
        actor_id: UUID,
        name: str | None = None,
        quantity: str | None = None,
    ) -> ListItem:
        lst = await self._load_for_actor(list_id, actor_id)
        item = lst.update_item(
            item_id=item_id,
            actor_id=actor_id,
            name=name,
            quantity=quantity,
        )
        await self._repo.update(lst)
        return item


class MarkItemPurchased(_ItemListUseCase):
    """Отметить товар купленным / не купленным (FR-23, FR-24)."""

    async def execute(
        self,
        list_id: UUID,
        item_id: UUID,
        actor_id: UUID,
        purchased: bool = True,
    ) -> ListItem:
        lst = await self._load_for_actor(list_id, actor_id)
        item = lst.mark_item_purchased(
            item_id=item_id, actor_id=actor_id, purchased=purchased
        )
        await self._repo.update(lst)
        return item


class DeleteItem(_ItemListUseCase):
    """Удалить товар из списка (FR-25)."""

    async def execute(self, list_id: UUID, item_id: UUID, actor_id: UUID) -> None:
        lst = await self._load_for_actor(list_id, actor_id)
        lst.remove_item(item_id=item_id, actor_id=actor_id)
        await self._repo.update(lst)
