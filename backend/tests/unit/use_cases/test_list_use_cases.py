"""Unit-тесты use cases управления списками покупок.

Тестируется оркестрация: use case должен загрузить агрегат, проверить
членство через методы корня, выполнить операцию и сохранить агрегат.
Инварианты (роли, уникальность) уже проверены в test_shopping_list.py,
поэтому здесь фокус на правильную последовательность и обработку
отсутствующих списков.
"""

from uuid import uuid4

import pytest

from tests.unit.fakes import InMemoryShoppingListRepository
from vibeshopping.domain.errors import (
    ListNotFoundError,
    NotListOwnerError,
)
from vibeshopping.services.lists import (
    CreateList,
    DeleteList,
    GetList,
    GetLists,
    RenameList,
)


@pytest.fixture
def repo() -> InMemoryShoppingListRepository:
    return InMemoryShoppingListRepository()


# ---------------------------------------------------------------------------
# CreateList
# ---------------------------------------------------------------------------


class TestCreateList:
    async def test_create_persists_list_with_owner(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        owner_id = uuid4()
        create = CreateList(repo=repo)

        lst = await create.execute(name="Продукты", owner_id=owner_id)

        assert lst.name == "Продукты"
        assert lst.owner_id == owner_id
        # сохранён в репозитории
        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert stored.owner_id == owner_id

    async def test_create_generates_id(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        create = CreateList(repo=repo)

        lst = await create.execute(name="List 1", owner_id=uuid4())

        assert lst.id is not None


# ---------------------------------------------------------------------------
# GetLists
# ---------------------------------------------------------------------------


class TestGetLists:
    async def test_returns_lists_where_user_is_member(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        # Один список, где user — владелец; другой, где не участник
        owner_id = uuid4()
        create = CreateList(repo=repo)
        await create.execute(name="My list", owner_id=owner_id)
        await create.execute(name="Someone else's", owner_id=uuid4())
        get_lists = GetLists(repo=repo)

        result = await get_lists.execute(user_id=owner_id)

        assert len(result) == 1
        assert result[0].name == "My list"

    async def test_returns_lists_where_user_is_member_not_owner(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        owner_id, member_id = uuid4(), uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="Shared", owner_id=owner_id)
        lst.invite_member(member_id, actor_id=owner_id)
        await repo.update(lst)
        get_lists = GetLists(repo=repo)

        result = await get_lists.execute(user_id=member_id)

        assert len(result) == 1
        assert result[0].id == lst.id

    async def test_user_without_lists_gets_empty(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        get_lists = GetLists(repo=repo)

        result = await get_lists.execute(user_id=uuid4())

        assert result == []


# ---------------------------------------------------------------------------
# GetList
# ---------------------------------------------------------------------------


class TestGetList:
    async def test_member_can_get_list(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        owner_id = uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="My list", owner_id=owner_id)
        get_list = GetList(repo=repo)

        result = await get_list.execute(list_id=lst.id, actor_id=owner_id)

        assert result.id == lst.id

    async def test_outsider_cannot_get_list(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        """Внешний пользователь получает 404, а не 403 — не раскрываем существование.

        Это принцип т.н. object-level authorization: не-участник не должен
        узнать, что список существует. Поэтому поднимаем ListNotFoundError,
        который HTTP-слой маппит в 404.
        """
        owner_id = uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="My list", owner_id=owner_id)
        get_list = GetList(repo=repo)

        with pytest.raises(ListNotFoundError):
            await get_list.execute(list_id=lst.id, actor_id=uuid4())

    async def test_unknown_list_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        get_list = GetList(repo=repo)

        with pytest.raises(ListNotFoundError):
            await get_list.execute(list_id=uuid4(), actor_id=uuid4())


# ---------------------------------------------------------------------------
# RenameList
# ---------------------------------------------------------------------------


class TestRenameList:
    async def test_owner_can_rename(self, repo: InMemoryShoppingListRepository) -> None:
        owner_id = uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="Old", owner_id=owner_id)
        rename = RenameList(repo=repo)

        result = await rename.execute(list_id=lst.id, new_name="New", actor_id=owner_id)

        assert result.name == "New"
        # изменение сохранено
        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert stored.name == "New"

    async def test_non_owner_cannot_rename(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        owner_id, member_id = uuid4(), uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="Old", owner_id=owner_id)
        lst.invite_member(member_id, actor_id=owner_id)
        await repo.update(lst)
        rename = RenameList(repo=repo)

        with pytest.raises(NotListOwnerError):
            await rename.execute(list_id=lst.id, new_name="Hack", actor_id=member_id)

    async def test_unknown_list_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        rename = RenameList(repo=repo)

        with pytest.raises(ListNotFoundError):
            await rename.execute(list_id=uuid4(), new_name="X", actor_id=uuid4())


# ---------------------------------------------------------------------------
# DeleteList
# ---------------------------------------------------------------------------


class TestDeleteList:
    async def test_owner_can_delete(self, repo: InMemoryShoppingListRepository) -> None:
        owner_id = uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="To delete", owner_id=owner_id)
        delete = DeleteList(repo=repo)

        await delete.execute(list_id=lst.id, actor_id=owner_id)

        assert await repo.get_by_id(lst.id) is None

    async def test_non_owner_cannot_delete(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        owner_id, member_id = uuid4(), uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="X", owner_id=owner_id)
        lst.invite_member(member_id, actor_id=owner_id)
        await repo.update(lst)
        delete = DeleteList(repo=repo)

        with pytest.raises(NotListOwnerError):
            await delete.execute(list_id=lst.id, actor_id=member_id)

        # список остался
        assert await repo.get_by_id(lst.id) is not None

    async def test_outsider_cannot_delete(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        """Внешний пользователь получает 404 — не раскрываем существование списка."""
        owner_id = uuid4()
        create = CreateList(repo=repo)
        lst = await create.execute(name="X", owner_id=owner_id)
        delete = DeleteList(repo=repo)

        with pytest.raises(ListNotFoundError):
            await delete.execute(list_id=lst.id, actor_id=uuid4())

    async def test_unknown_list_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        delete = DeleteList(repo=repo)

        with pytest.raises(ListNotFoundError):
            await delete.execute(list_id=uuid4(), actor_id=uuid4())
