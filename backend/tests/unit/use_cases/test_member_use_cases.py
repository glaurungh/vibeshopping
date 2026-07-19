"""Unit-тесты use cases управления участниками списка.

Покрытие: приглашение (FR-30, FR-32), удаление (FR-33, FR-34),
выход из списка (FR-36), передача владения (FR-35).
"""

from uuid import uuid4

import pytest

from tests.unit.fakes import InMemoryShoppingListRepository
from vibeshopping.domain.errors import (
    CannotRemoveOwnerError,
    ListNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    NotListOwnerError,
    OwnerCannotLeaveError,
)
from vibeshopping.services.lists import CreateList
from vibeshopping.services.members import (
    InviteMember,
    LeaveList,
    RemoveMember,
    TransferOwnership,
)


@pytest.fixture
def repo() -> InMemoryShoppingListRepository:
    return InMemoryShoppingListRepository()


async def _make_list_with_owner(repo: InMemoryShoppingListRepository, owner_id=None):
    owner_id = owner_id or uuid4()
    lst = await CreateList(repo=repo).execute(name="L", owner_id=owner_id)
    return lst, owner_id


async def _make_list_with_member(
    repo: InMemoryShoppingListRepository,
):
    lst, owner_id = await _make_list_with_owner(repo)
    member_id = uuid4()
    lst.invite_member(member_id, actor_id=owner_id)
    await repo.update(lst)
    return lst, owner_id, member_id


# ---------------------------------------------------------------------------
# InviteMember
# ---------------------------------------------------------------------------


class TestInviteMember:
    async def test_owner_can_invite(self, repo: InMemoryShoppingListRepository) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        member_id = uuid4()
        invite = InviteMember(repo=repo)

        member = await invite.execute(
            list_id=lst.id, user_id=member_id, actor_id=owner_id
        )

        assert member.user_id == member_id
        # сохранён в агрегате
        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert stored.is_member(member_id)

    async def test_member_cannot_invite_others(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        invite = InviteMember(repo=repo)

        with pytest.raises(NotListOwnerError):
            await invite.execute(list_id=lst.id, user_id=uuid4(), actor_id=member_id)

    async def test_invite_duplicate_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        invite = InviteMember(repo=repo)

        with pytest.raises(MemberAlreadyExistsError):
            await invite.execute(list_id=lst.id, user_id=member_id, actor_id=owner_id)

    async def test_unknown_list_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        invite = InviteMember(repo=repo)

        with pytest.raises(ListNotFoundError):
            await invite.execute(list_id=uuid4(), user_id=uuid4(), actor_id=uuid4())


# ---------------------------------------------------------------------------
# RemoveMember
# ---------------------------------------------------------------------------


class TestRemoveMember:
    async def test_owner_can_remove_member(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        remove = RemoveMember(repo=repo)

        await remove.execute(list_id=lst.id, user_id=member_id, actor_id=owner_id)

        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert not stored.is_member(member_id)

    async def test_owner_cannot_remove_self(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, _ = await _make_list_with_member(repo)
        remove = RemoveMember(repo=repo)

        with pytest.raises(CannotRemoveOwnerError):
            await remove.execute(list_id=lst.id, user_id=owner_id, actor_id=owner_id)

    async def test_member_cannot_remove_others(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        third_id = uuid4()
        lst.invite_member(third_id, actor_id=owner_id)
        await repo.update(lst)
        remove = RemoveMember(repo=repo)

        with pytest.raises(NotListOwnerError):
            await remove.execute(list_id=lst.id, user_id=third_id, actor_id=member_id)


# ---------------------------------------------------------------------------
# LeaveList
# ---------------------------------------------------------------------------


class TestLeaveList:
    async def test_member_can_leave(self, repo: InMemoryShoppingListRepository) -> None:
        lst, _, member_id = await _make_list_with_member(repo)
        leave = LeaveList(repo=repo)

        await leave.execute(list_id=lst.id, user_id=member_id)

        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert not stored.is_member(member_id)

    async def test_owner_cannot_leave(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, _ = await _make_list_with_member(repo)
        leave = LeaveList(repo=repo)

        with pytest.raises(OwnerCannotLeaveError):
            await leave.execute(list_id=lst.id, user_id=owner_id)


# ---------------------------------------------------------------------------
# TransferOwnership
# ---------------------------------------------------------------------------


class TestTransferOwnership:
    async def test_owner_can_transfer(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        transfer = TransferOwnership(repo=repo)

        await transfer.execute(
            list_id=lst.id, new_owner_id=member_id, actor_id=owner_id
        )

        stored = await repo.get_by_id(lst.id)
        assert stored is not None
        assert stored.owner_id == member_id
        # бывший владелец остаётся участником
        assert stored.is_member(owner_id)

    async def test_member_cannot_transfer(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id, member_id = await _make_list_with_member(repo)
        transfer = TransferOwnership(repo=repo)

        with pytest.raises(NotListOwnerError):
            await transfer.execute(
                list_id=lst.id, new_owner_id=owner_id, actor_id=member_id
            )

    async def test_transfer_to_non_member_raises(
        self, repo: InMemoryShoppingListRepository
    ) -> None:
        lst, owner_id = await _make_list_with_owner(repo)
        transfer = TransferOwnership(repo=repo)

        with pytest.raises(MemberNotFoundError):
            await transfer.execute(
                list_id=lst.id, new_owner_id=uuid4(), actor_id=owner_id
            )
