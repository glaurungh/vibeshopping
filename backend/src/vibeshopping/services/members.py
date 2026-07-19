"""Use cases управления участниками списка.

Покрытие (см. docs/spec.md):
    - FR-30: только владелец может приглашать
    - FR-32: нельзя пригласить дважды
    - FR-33: только владелец может удалять участников
    - FR-34: владелец не может удалить себя
    - FR-35: передача владения
    - FR-36: участник может покинуть список

Инварианты защищены методами агрегата; здесь — оркестрация.
Для не-владельца операций invite/remove/transfer поднимается
NotListOwnerError (он маппится в 403 — это осмысленно, т.к. пользователь
видит, что список существует, но ему не хватает прав).
"""

from uuid import UUID

from vibeshopping.domain.errors import ListNotFoundError
from vibeshopping.domain.repositories import ShoppingListRepository
from vibeshopping.domain.shopping_list import ListMember, ShoppingList


class _MemberListUseCase:
    """Базовый класс: загрузка агрегата с проверкой существования.

    Для операций с участниками валиден любой участник списка (не только
    владелец); дальнейшая проверка прав выполняется в методах агрегата.
    """

    def __init__(self, repo: ShoppingListRepository) -> None:
        self._repo = repo

    async def _load_existing(self, list_id: UUID) -> ShoppingList:
        lst = await self._repo.get_by_id(list_id)
        if lst is None:
            raise ListNotFoundError(list_id)
        return lst


class InviteMember(_MemberListUseCase):
    """Пригласить пользователя в список (FR-30, FR-32)."""

    async def execute(self, list_id: UUID, user_id: UUID, actor_id: UUID) -> ListMember:
        lst = await self._load_existing(list_id)
        member = lst.invite_member(user_id=user_id, actor_id=actor_id)
        await self._repo.update(lst)
        return member


class RemoveMember(_MemberListUseCase):
    """Удалить участника (FR-33, FR-34)."""

    async def execute(self, list_id: UUID, user_id: UUID, actor_id: UUID) -> None:
        lst = await self._load_existing(list_id)
        lst.remove_member(user_id=user_id, actor_id=actor_id)
        await self._repo.update(lst)


class LeaveList(_MemberListUseCase):
    """Участник покидает список (FR-36)."""

    async def execute(self, list_id: UUID, user_id: UUID) -> None:
        lst = await self._load_existing(list_id)
        lst.leave(user_id=user_id)
        await self._repo.update(lst)


class TransferOwnership(_MemberListUseCase):
    """Передать владение другому участнику (FR-35)."""

    async def execute(self, list_id: UUID, new_owner_id: UUID, actor_id: UUID) -> None:
        lst = await self._load_existing(list_id)
        lst.transfer_ownership_to(new_owner_id=new_owner_id, actor_id=actor_id)
        await self._repo.update(lst)
