"""Unit-тесты use cases управления элементами списка.

Элементы — часть агрегата ShoppingList, доступ через корень. Инварианты
(права участников) уже протестированы на агрегате; здесь проверяем
оркестрацию: загрузка агрегата, вызов метода, сохранение целиком.
"""

from uuid import uuid4

import pytest

from tests.unit.fakes import InMemoryShoppingListRepository
from vibeshopping.domain.errors import (
    ListItemNotFoundError,
    ListNotFoundError,
)
from vibeshopping.services.items import (
    AddItem,
    DeleteItem,
    MarkItemPurchased,
    UpdateItem,
)
from vibeshopping.services.lists import CreateList


@pytest.fixture
def repo() -> InMemoryShoppingListRepository:
    return InMemoryShoppingListRepository()


async def _make_list_with_owner(repo: InMemoryShoppingListRepository, owner_id=None):
    owner_id = owner_id or uuid4()
    lst = await CreateList(repo=repo).execute(name="L", owner_id=owner_id)
    return lst, owner_id


# ---------------------------------------------------------------------------
# AddItem
# ---------------------------------------------------------------------------


class TestAddItem:
    async def test_member_can_add_item(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        add = AddItem(repo=repo)

        item = await add.execute(
            list_id=lst.id, name="Молоко", actor_id=owner_id, quantity="1 л"
        )

        assert item.name == "Молоко"
        # сохранено в агрегате
        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert any(i.id == item.id for i in stored.items)

    async def test_unknown_list_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        add = AddItem(repo=repo)

        with pytest.raises(ListNotFoundError):
            await add.execute(list_id=uuid4(), name="X", actor_id=uuid4())


# ---------------------------------------------------------------------------
# UpdateItem
# ---------------------------------------------------------------------------


class TestUpdateItem:
    async def test_update_name_and_quantity(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        add = AddItem(repo=repo)
        item = await add.execute(
            list_id=lst.id, name="Молоко", actor_id=owner_id, quantity="1 л"
        )
        update = UpdateItem(repo=repo)

        result = await update.execute(
            list_id=lst.id,
            item_id=item.id,
            actor_id=owner_id,
            name="Кефир",
            quantity="2 шт",
        )

        assert result.name == "Кефир"
        assert result.quantity == "2 шт"

    async def test_partial_update_keeps_other_fields(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        add = AddItem(repo=repo)
        item = await add.execute(
            list_id=lst.id, name="Молоко", actor_id=owner_id, quantity="1 л"
        )
        update = UpdateItem(repo=repo)

        # меняем только name
        await update.execute(
            list_id=lst.id,
            item_id=item.id,
            actor_id=owner_id,
            name="Кефир",
        )

        # quantity должен сохраниться
        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        updated_item = next(i for i in stored.items if i.id == item.id)
        assert updated_item.quantity == "1 л"

    async def test_outsider_cannot_update(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        add = AddItem(repo=repo)
        item = await add.execute(list_id=lst.id, name="X", actor_id=owner_id)
        update = UpdateItem(repo=repo)

        with pytest.raises(ListNotFoundError):
            await update.execute(
                list_id=lst.id,
                item_id=item.id,
                actor_id=uuid4(),
                name="Hack",
            )

    async def test_unknown_item_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        update = UpdateItem(repo=repo)

        with pytest.raises(ListItemNotFoundError):
            await update.execute(
                list_id=lst.id,
                item_id=uuid4(),
                actor_id=owner_id,
                name="X",
            )


# ---------------------------------------------------------------------------
# MarkItemPurchased
# ---------------------------------------------------------------------------


class TestMarkItemPurchased:
    async def test_mark_purchased_true(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        mark = MarkItemPurchased(repo=repo)

        result = await mark.execute(
            list_id=lst.id, item_id=item.id, actor_id=owner_id, purchased=True
        )

        assert result.purchased is True

    async def test_mark_purchased_false_again(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        mark = MarkItemPurchased(repo=repo)
        await mark.execute(
            list_id=lst.id, item_id=item.id, actor_id=owner_id, purchased=True
        )

        result = await mark.execute(
            list_id=lst.id, item_id=item.id, actor_id=owner_id, purchased=False
        )

        assert result.purchased is False

    async def test_outsider_cannot_mark(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        mark = MarkItemPurchased(repo=repo)

        with pytest.raises(ListNotFoundError):
            await mark.execute(
                list_id=lst.id,
                item_id=item.id,
                actor_id=uuid4(),
                purchased=True,
            )


# ---------------------------------------------------------------------------
# DeleteItem
# ---------------------------------------------------------------------------


class TestDeleteItem:
    async def test_owner_can_delete(self, repo: InMemoryShoppingListRepository) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        delete = DeleteItem(repo=repo)

        await delete.execute(list_id=lst.id, item_id=item.id, actor_id=owner_id)

        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert not any(i.id == item.id for i in stored.items)

    async def test_outsider_cannot_delete(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        delete = DeleteItem(repo=repo)

        with pytest.raises(ListNotFoundError):
            await delete.execute(list_id=lst.id, item_id=item.id, actor_id=uuid4())

    async def test_member_can_delete_others_item(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        """FR-32: участник может удалять любые элементы в списке."""
        lst, owner_id = await _make_list_with_owner(repo)
        member_id = uuid4()
        lst.invite_member(member_id, actor_id=owner_id)
        await repo.update(lst)
        item = await AddItem(repo=repo).execute(
            list_id=lst.id, name="X", actor_id=owner_id
        )
        delete = DeleteItem(repo=repo)

        await delete.execute(list_id=lst.id, item_id=item.id, actor_id=member_id)

        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert not any(i.id == item.id for i in stored.items)

    async def test_unknown_item_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        delete = DeleteItem(repo=repo)

        with pytest.raises(ListItemNotFoundError):
            await delete.execute(list_id=lst.id, item_id=uuid4(), actor_id=owner_id)
