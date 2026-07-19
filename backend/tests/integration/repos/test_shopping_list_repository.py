"""Интеграционные тесты SqlAlchemyShoppingListRepository.

Проверяем, что агрегат ShoppingList (с items и members) корректно
сохраняется и загружается из PostgreSQL. Маппинг 3 таблиц → 1 доменная
модель — ключевой тест инфраструктуры.
"""

from uuid import uuid4

from vibeshopping.domain.shopping_list import (
    MemberRole,
    ShoppingList,
)
from vibeshopping.infrastructure.tables import (
    list_items,
    list_members,
    shopping_lists,
)
from vibeshopping.repos.shopping_list_repository import SqlAlchemyShoppingListRepository


async def _create_owner_and_repo(db_session):
    from sqlalchemy import insert

    from vibeshopping.infrastructure.tables import users

    owner_id = uuid4()
    await db_session.execute(
        insert(users).values(
            id=owner_id,
            email=f"{owner_id}@test.com",
            hashed_password="hash",
        )
    )
    await db_session.commit()
    repo = SqlAlchemyShoppingListRepository(db_session)
    return repo, owner_id


class TestShoppingListRepository:
    async def test_add_persists_aggregate(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="Продукты", owner_id=owner_id)

        result = await repo.add(lst)

        assert result.id == lst.id
        # Проверяем, что 3 таблицы заполнены
        from sqlalchemy import select

        list_row = (
            await db_session.execute(
                select(shopping_lists).where(shopping_lists.c.id == lst.id)
            )
        ).first()
        assert list_row is not None
        assert list_row.name == "Продукты"

        member_rows = (
            await db_session.execute(
                select(list_members).where(list_members.c.list_id == lst.id)
            )
        ).all()
        assert len(member_rows) == 1
        assert member_rows[0].user_id == owner_id
        assert member_rows[0].role == "owner"

    async def test_get_by_id_loads_full_aggregate(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="Мой список", owner_id=owner_id)
        lst.add_item(name="Молоко", actor_id=owner_id, quantity="1 л")
        lst.add_item(name="Хлеб", actor_id=owner_id)
        await repo.add(lst)

        result = await repo.get_by_id(lst.id)

        assert result is not None
        assert result.name == "Мой список"
        assert len(result.members) == 1
        assert result.owner_id == owner_id
        assert len(result.items) == 2
        item_names = {i.name for i in result.items}
        assert item_names == {"Молоко", "Хлеб"}

    async def test_get_by_id_returns_none_for_unknown(self, db_session) -> None:
        repo, _ = await _create_owner_and_repo(db_session)

        result = await repo.get_by_id(uuid4())

        assert result is None

    async def test_get_all_for_user_returns_own_lists(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst1 = ShoppingList.create(name="L1", owner_id=owner_id)
        lst2 = ShoppingList.create(name="L2", owner_id=owner_id)
        await repo.add(lst1)
        await repo.add(lst2)

        result = await repo.get_all_for_user(owner_id)

        assert len(result) == 2
        names = {lst.name for lst in result}
        assert names == {"L1", "L2"}

    async def test_get_all_for_user_excludes_non_member_lists(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="Mine", owner_id=owner_id)
        await repo.add(lst)
        # Другой пользователь — separate repo, но та же сессия
        _, other_id = await _create_owner_and_repo(db_session)
        ShoppingList.create(name="Other", owner_id=other_id)
        await repo.add(ShoppingList.create(name="Other", owner_id=other_id))

        result = await repo.get_all_for_user(owner_id)

        assert len(result) == 1
        assert result[0].name == "Mine"

    async def test_get_all_for_user_includes_shared_lists(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        # Создаём второго пользователя
        from sqlalchemy import insert

        member_id = uuid4()
        from vibeshopping.infrastructure.tables import users

        await db_session.execute(
            insert(users).values(
                id=member_id,
                email=f"{member_id}@test.com",
                hashed_password="hash",
            )
        )
        await db_session.commit()

        lst = ShoppingList.create(name="Shared", owner_id=owner_id)
        lst.invite_member(member_id, actor_id=owner_id)
        await repo.add(lst)

        result = await repo.get_all_for_user(member_id)

        assert len(result) == 1
        assert result[0].name == "Shared"

    async def test_update_persists_changes(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="Old", owner_id=owner_id)
        await repo.add(lst)

        lst.rename(new_name="New", actor_id=owner_id)
        lst.add_item(name="Молоко", actor_id=owner_id)
        result = await repo.update(lst)

        assert result.name == "New"
        # Перезагрузим из БД для проверки
        reloaded = await repo.get_by_id(lst.id)
        assert reloaded is not None
        assert reloaded.name == "New"
        assert len(reloaded.items) == 1
        assert reloaded.items[0].name == "Молоко"

    async def test_delete_removes_all_data(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="Delete me", owner_id=owner_id)
        lst.add_item(name="X", actor_id=owner_id)
        await repo.add(lst)

        await repo.delete(lst.id)

        assert await repo.get_by_id(lst.id) is None
        # Таблицы list_items и list_members должны быть пустыми
        from sqlalchemy import select

        items = (
            await db_session.execute(
                select(list_items).where(list_items.c.list_id == lst.id)
            )
        ).all()
        assert len(items) == 0

        members = (
            await db_session.execute(
                select(list_members).where(list_members.c.list_id == lst.id)
            )
        ).all()
        assert len(members) == 0

    async def test_purchased_flag_persists(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        lst = ShoppingList.create(name="L", owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)
        lst.mark_item_purchased(item.id, actor_id=owner_id, purchased=True)
        await repo.add(lst)

        reloaded = await repo.get_by_id(lst.id)

        assert reloaded is not None
        assert reloaded.items[0].purchased is True

    async def test_member_role_persists(self, db_session) -> None:
        repo, owner_id = await _create_owner_and_repo(db_session)
        from sqlalchemy import insert

        member_id = uuid4()
        from vibeshopping.infrastructure.tables import users

        await db_session.execute(
            insert(users).values(
                id=member_id,
                email=f"{member_id}@test.com",
                hashed_password="hash",
            )
        )
        await db_session.commit()

        lst = ShoppingList.create(name="L", owner_id=owner_id)
        lst.invite_member(member_id, actor_id=owner_id)
        lst.transfer_ownership_to(member_id, actor_id=owner_id)
        await repo.add(lst)

        reloaded = await repo.get_by_id(lst.id)

        assert reloaded is not None
        assert reloaded.owner_id == member_id
        old_owner_member = next(m for m in reloaded.members if m.user_id == owner_id)
        assert old_owner_member.role == MemberRole.MEMBER
