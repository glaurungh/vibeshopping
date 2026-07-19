"""Реализация ShoppingListRepository на SQLAlchemy Core.

Загружает **целый агрегат** (с items и members) из 3 таблиц:
shopping_lists, list_members, list_items. Маппинг строк → доменная
модель — вручную. См. docs/architecture.md, разделы
«SQLAlchemy Core, а не ORM» и «Агрегаты и инварианты».
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibeshopping.domain.shopping_list import (
    ListItem,
    ListMember,
    MemberRole,
    ShoppingList,
)
from vibeshopping.infrastructure.tables import (
    list_items,
    list_members,
    shopping_lists,
)


class SqlAlchemyShoppingListRepository:
    """Реализация ShoppingListRepository на SQLAlchemy Core + asyncpg."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, list_id: UUID) -> ShoppingList | None:
        row = (
            await self._session.execute(
                select(shopping_lists).where(shopping_lists.c.id == list_id)
            )
        ).first()
        if row is None:
            return None
        return await self._load_aggregate(row, list_id)

    async def get_all_for_user(self, user_id: UUID) -> list[ShoppingList]:
        # Находим все list_id, где user — участник
        list_ids_stmt = select(list_members.c.list_id).where(
            list_members.c.user_id == user_id
        )
        list_ids_result = await self._session.execute(list_ids_stmt)
        list_ids = [r for (r,) in list_ids_result.all()]
        if not list_ids:
            return []

        result = []
        for lid in list_ids:
            lst = await self.get_by_id(lid)
            if lst is not None:
                result.append(lst)
        return result

    async def add(self, shopping_list: ShoppingList) -> ShoppingList:
        await self._session.execute(
            shopping_lists.insert().values(
                id=shopping_list.id,
                name=shopping_list.name,
                created_at=shopping_list.created_at,
            )
        )
        await self._insert_members(shopping_list)
        await self._insert_items(shopping_list)
        await self._session.commit()
        return shopping_list

    async def update(self, shopping_list: ShoppingList) -> ShoppingList:
        await self._session.execute(
            shopping_lists.update()
            .where(shopping_lists.c.id == shopping_list.id)
            .values(
                name=shopping_list.name,
            )
        )
        # Переписываем members и items (delete + insert — проще для агрегата)
        await self._session.execute(
            list_members.delete().where(list_members.c.list_id == shopping_list.id)
        )
        await self._insert_members(shopping_list)
        await self._session.execute(
            list_items.delete().where(list_items.c.list_id == shopping_list.id)
        )
        await self._insert_items(shopping_list)
        await self._session.commit()
        return shopping_list

    async def delete(self, list_id: UUID) -> None:
        # CASCADE удалит items и members автоматически
        await self._session.execute(
            shopping_lists.delete().where(shopping_lists.c.id == list_id)
        )
        await self._session.commit()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_aggregate(self, list_row: Any, list_id: UUID) -> ShoppingList:
        """Загрузить полный агрегат: список + members + items."""
        members_rows = (
            await self._session.execute(
                select(list_members).where(list_members.c.list_id == list_id)
            )
        ).all()

        items_rows = (
            await self._session.execute(
                select(list_items).where(list_items.c.list_id == list_id)
            )
        ).all()

        return ShoppingList(
            id=list_row.id,
            name=list_row.name,
            created_at=list_row.created_at,
            members=[_row_to_member(r) for r in members_rows],
            items=[_row_to_item(r) for r in items_rows],
        )

    async def _insert_members(self, shopping_list: ShoppingList) -> None:
        for m in shopping_list.members:
            await self._session.execute(
                list_members.insert().values(
                    list_id=shopping_list.id,
                    user_id=m.user_id,
                    role=m.role.value,
                    joined_at=m.joined_at,
                )
            )

    async def _insert_items(self, shopping_list: ShoppingList) -> None:
        for item in shopping_list.items:
            await self._session.execute(
                list_items.insert().values(
                    id=item.id,
                    list_id=shopping_list.id,
                    name=item.name,
                    quantity=item.quantity,
                    purchased=item.purchased,
                    created_at=item.created_at,
                )
            )


def _row_to_member(row: Any) -> ListMember:
    return ListMember(
        user_id=row.user_id,
        role=MemberRole(row.role),
        joined_at=row.joined_at,
    )


def _row_to_item(row: Any) -> ListItem:
    return ListItem(
        id=row.id,
        name=row.name,
        quantity=row.quantity,
        purchased=row.purchased,
        created_at=row.created_at,
    )
