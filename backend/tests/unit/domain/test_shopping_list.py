"""Unit-тесты агрегата ShoppingList.

ShoppingList — корень агрегата. Тестируются все инварианты из docs/spec.md:
- FR-11: при создании владелец становится участником
- FR-13: только владелец может переименовать/удалить список
- FR-21..25: управление элементами (владелец и участники)
- FR-30..36: управление участниками и владением
"""

from uuid import UUID, uuid4

import pytest

from vibeshopping.domain.errors import (
    CannotRemoveOwnerError,
    ListItemNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    NotListMemberError,
    NotListOwnerError,
    OwnerCannotLeaveError,
)
from vibeshopping.domain.shopping_list import (
    ListItem,
    ListMember,
    MemberRole,
    ShoppingList,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list(owner_id: UUID | None = None, name: str = "Продукты") -> ShoppingList:
    """Создаёт валидный список с указанным владельцем."""
    return ShoppingList.create(name=name, owner_id=owner_id or uuid4())


def _make_list_with_two_members(
    owner_id: UUID | None = None, member_id: UUID | None = None
) -> tuple[ShoppingList, UUID, UUID]:
    """Создаёт список с владельцем и одним участником."""
    owner_id = owner_id or uuid4()
    member_id = member_id or uuid4()
    lst = ShoppingList.create(name="Продукты", owner_id=owner_id)
    lst.invite_member(member_id, actor_id=owner_id)
    return lst, owner_id, member_id


# ---------------------------------------------------------------------------
# Создание списка (FR-11)
# ---------------------------------------------------------------------------


class TestCreateList:
    def test_create_list_adds_owner_as_member(self) -> None:
        owner_id = uuid4()

        lst = ShoppingList.create(name="Продукты", owner_id=owner_id)

        assert lst.name == "Продукты"
        assert len(lst.members) == 1
        assert lst.members[0].user_id == owner_id
        assert lst.members[0].role == MemberRole.OWNER

    def test_create_list_has_no_items_initially(self) -> None:
        lst = _make_list()

        assert lst.items == []

    def test_new_list_generates_id(self) -> None:
        lst1 = _make_list()
        lst2 = _make_list()

        assert isinstance(lst1.id, UUID)
        assert lst1.id != lst2.id

    def test_new_list_has_created_at(self) -> None:
        lst = _make_list()

        assert lst.created_at is not None


# ---------------------------------------------------------------------------
# Свойства-проекции: owner_id, member_ids, is_member, is_owner
# ---------------------------------------------------------------------------


class TestListProjections:
    def test_owner_id_returns_owner_user_id(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        assert lst.owner_id == owner_id

    def test_is_member_returns_true_for_owner_and_members(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        assert lst.is_member(owner_id) is True
        assert lst.is_member(member_id) is True

    def test_is_member_returns_false_for_outsider(self) -> None:
        lst = _make_list()

        assert lst.is_member(uuid4()) is False

    def test_is_owner_returns_true_only_for_owner(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        assert lst.is_owner(owner_id) is True
        assert lst.is_owner(member_id) is False


# ---------------------------------------------------------------------------
# Переименование (FR-13)
# ---------------------------------------------------------------------------


class TestRenameList:
    def test_owner_can_rename(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        lst.rename(new_name="Новый год", actor_id=owner_id)

        assert lst.name == "Новый год"

    def test_non_owner_cannot_rename(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        with pytest.raises(NotListOwnerError):
            lst.rename(new_name="Взлом", actor_id=member_id)

    def test_outsider_cannot_rename(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(NotListOwnerError):
            lst.rename(new_name="Взлом", actor_id=uuid4())


# ---------------------------------------------------------------------------
# Управление участниками (FR-30..36)
# ---------------------------------------------------------------------------


class TestInviteMember:
    def test_owner_can_invite_member(self) -> None:
        owner_id, member_id = uuid4(), uuid4()
        lst = _make_list(owner_id=owner_id)

        member = lst.invite_member(member_id, actor_id=owner_id)

        assert member.user_id == member_id
        assert member.role == MemberRole.MEMBER
        assert lst.is_member(member_id) is True

    def test_non_owner_cannot_invite(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()
        third_user = uuid4()

        with pytest.raises(NotListOwnerError):
            lst.invite_member(third_user, actor_id=member_id)

    def test_cannot_invite_same_user_twice(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        with pytest.raises(MemberAlreadyExistsError):
            lst.invite_member(member_id, actor_id=owner_id)

    def test_cannot_invite_owner_again(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(MemberAlreadyExistsError):
            lst.invite_member(owner_id, actor_id=owner_id)


class TestRemoveMember:
    def test_owner_can_remove_member(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        lst.remove_member(member_id, actor_id=owner_id)

        assert not lst.is_member(member_id)

    def test_non_owner_cannot_remove(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()
        third_user = uuid4()
        lst.invite_member(third_user, actor_id=owner_id)

        with pytest.raises(NotListOwnerError):
            lst.remove_member(third_user, actor_id=member_id)

    def test_owner_cannot_remove_self(self) -> None:
        lst, owner_id, _ = _make_list_with_two_members()

        with pytest.raises(CannotRemoveOwnerError):
            lst.remove_member(owner_id, actor_id=owner_id)

    def test_removing_non_existing_member_raises(self) -> None:
        lst, owner_id, _ = _make_list_with_two_members()

        with pytest.raises(MemberNotFoundError):
            lst.remove_member(uuid4(), actor_id=owner_id)


class TestLeaveList:
    def test_member_can_leave(self) -> None:
        lst, _, member_id = _make_list_with_two_members()

        lst.leave(member_id)

        assert not lst.is_member(member_id)

    def test_owner_cannot_leave(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(OwnerCannotLeaveError):
            lst.leave(owner_id)

    def test_outsider_cannot_leave(self) -> None:
        lst = _make_list()

        with pytest.raises(MemberNotFoundError):
            lst.leave(uuid4())


class TestTransferOwnership:
    def test_owner_can_transfer_to_member(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        lst.transfer_ownership_to(member_id, actor_id=owner_id)

        assert lst.owner_id == member_id
        assert lst.is_owner(member_id) is True
        assert lst.is_owner(owner_id) is False
        # бывший владелец остаётся участником
        assert lst.is_member(owner_id) is True

    def test_transfer_keeps_members_count(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()
        count_before = len(lst.members)

        lst.transfer_ownership_to(member_id, actor_id=owner_id)

        assert len(lst.members) == count_before

    def test_non_owner_cannot_transfer(self) -> None:
        lst, owner_id, member_id = _make_list_with_two_members()

        with pytest.raises(NotListOwnerError):
            lst.transfer_ownership_to(owner_id, actor_id=member_id)

    def test_cannot_transfer_to_non_member(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(MemberNotFoundError):
            lst.transfer_ownership_to(uuid4(), actor_id=owner_id)


# ---------------------------------------------------------------------------
# Управление элементами (FR-21..25)
# ---------------------------------------------------------------------------


class TestAddItem:
    def test_owner_can_add_item(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        item = lst.add_item(name="Молоко", actor_id=owner_id)

        assert item.name == "Молоко"
        assert item.quantity is None
        assert item.purchased is False
        assert item in lst.items

    def test_member_can_add_item(self) -> None:
        lst, _, member_id = _make_list_with_two_members()

        item = lst.add_item(name="Хлеб", actor_id=member_id, quantity="2 шт")

        assert item.name == "Хлеб"
        assert item.quantity == "2 шт"

    def test_outsider_cannot_add_item(self) -> None:
        lst = _make_list()

        with pytest.raises(NotListMemberError):
            lst.add_item(name="Взлом", actor_id=uuid4())

    def test_adding_two_items_generates_unique_ids(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        item1 = lst.add_item(name="Молоко", actor_id=owner_id)
        item2 = lst.add_item(name="Хлеб", actor_id=owner_id)

        assert item1.id != item2.id


class TestUpdateItem:
    def test_owner_can_update_item_name(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)

        lst.update_item(item.id, actor_id=owner_id, name="Кефир")

        assert item.name == "Кефир"

    def test_member_can_update_item_quantity(self) -> None:
        lst, _, member_id = _make_list_with_two_members()
        item = lst.add_item(name="Сахар", actor_id=member_id)

        lst.update_item(item.id, actor_id=member_id, quantity="500 г")

        assert item.quantity == "500 г"

    def test_none_values_keep_existing(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id, quantity="1 л")

        lst.update_item(item.id, actor_id=owner_id, name="Кефир")
        # quantity не передан → должен сохраниться

        assert item.name == "Кефир"
        assert item.quantity == "1 л"

    def test_outsider_cannot_update_item(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)

        with pytest.raises(NotListMemberError):
            lst.update_item(item.id, actor_id=uuid4(), name="Взлом")

    def test_update_non_existing_item_raises(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(ListItemNotFoundError):
            lst.update_item(uuid4(), actor_id=owner_id, name="Нет такого")


class TestMarkItemPurchased:
    def test_member_can_mark_item_purchased(self) -> None:
        lst, _, member_id = _make_list_with_two_members()
        item = lst.add_item(name="Молоко", actor_id=member_id)

        lst.mark_item_purchased(item.id, actor_id=member_id)

        assert item.purchased is True

    def test_can_mark_purchased_false_again(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)
        lst.mark_item_purchased(item.id, actor_id=owner_id, purchased=True)

        lst.mark_item_purchased(item.id, actor_id=owner_id, purchased=False)

        assert item.purchased is False

    def test_outsider_cannot_mark_item(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)

        with pytest.raises(NotListMemberError):
            lst.mark_item_purchased(item.id, actor_id=uuid4())


class TestRemoveItem:
    def test_owner_can_remove_item(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)

        lst.remove_item(item.id, actor_id=owner_id)

        assert item not in lst.items

    def test_member_can_remove_item(self) -> None:
        lst, _, member_id = _make_list_with_two_members()
        item = lst.add_item(name="Молоко", actor_id=member_id)

        lst.remove_item(item.id, actor_id=member_id)

        assert item not in lst.items

    def test_outsider_cannot_remove_item(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)
        item = lst.add_item(name="Молоко", actor_id=owner_id)

        with pytest.raises(NotListMemberError):
            lst.remove_item(item.id, actor_id=uuid4())

    def test_remove_non_existing_item_raises(self) -> None:
        owner_id = uuid4()
        lst = _make_list(owner_id=owner_id)

        with pytest.raises(ListItemNotFoundError):
            lst.remove_item(uuid4(), actor_id=owner_id)


# ---------------------------------------------------------------------------
# Модели ListItem и ListMember напрямую
# ---------------------------------------------------------------------------


class TestListItemDefaults:
    def test_list_item_defaults(self) -> None:
        item = ListItem(name="Молоко")

        assert isinstance(item.id, UUID)
        assert item.name == "Молоко"
        assert item.quantity is None
        assert item.purchased is False
        assert item.created_at is not None


class TestListMemberDefaults:
    def test_member_role_values(self) -> None:
        assert MemberRole.OWNER == "owner"
        assert MemberRole.MEMBER == "member"

    def test_list_member_fields(self) -> None:
        member = ListMember(user_id=uuid4(), role=MemberRole.MEMBER)

        assert member.role == MemberRole.MEMBER
        assert member.joined_at is not None
