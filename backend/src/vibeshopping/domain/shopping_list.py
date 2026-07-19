"""Агрегат ShoppingList.

ShoppingList — корень агрегата. ListItem и ListMember — внутренние части;
доступ к ним возможен только через методы корня. Все инварианты из
docs/spec.md (FR-13, FR-21..25, FR-30..36) защищаются внутри методов —
создать список в недопустимом состоянии через публичный API нельзя.

См. docs/architecture.md, разделы «Агрегаты и инварианты» и
«Богатые vs анемичные модели».
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from vibeshopping.domain.errors import (
    CannotRemoveOwnerError,
    ListItemNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    NotListMemberError,
    NotListOwnerError,
    OwnerCannotLeaveError,
)


class MemberRole(StrEnum):
    """Роль участника списка (см. FR-30..36)."""

    OWNER = "owner"
    MEMBER = "member"


class ListMember(BaseModel):
    """Участник списка. Роль определяет права (owner/member)."""

    user_id: UUID
    role: MemberRole
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ListItem(BaseModel):
    """Элемент списка покупок.

    Атрибуты:
        name: название товара (например, «Молоко»).
        quantity: свободное описание количества («2 кг», «пачка», None).
        purchased: флаг «куплено» (FR-23, FR-24).
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    quantity: str | None = None
    purchased: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ShoppingList(BaseModel):
    """Корень агрегата «Список покупок».

    Инварианты, поддерживаемые агрегатом:
        - Ровно один участник имеет роль owner (FR-11).
        - Один пользователь не может быть участником дважды (FR-32).
        - Только владелец может переименовывать список, приглашать и
          удалять участников, передавать владение (FR-13, FR-30, FR-33, FR-35).
        - Владелец не может покинуть список или быть удалён (FR-34, FR-36).
        - Только участники могут управлять элементами (FR-21..25).
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    members: list[ListMember] = Field(default_factory=list)
    items: list[ListItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # Фабричный метод
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str, owner_id: UUID) -> "ShoppingList":
        """Создать новый список.

        Владелец автоматически становится участником со ролью owner (FR-11).
        """
        now = datetime.now(UTC)
        return cls(
            name=name,
            members=[
                ListMember(user_id=owner_id, role=MemberRole.OWNER, joined_at=now)
            ],
        )

    # ------------------------------------------------------------------
    # Свойства-проекции (только чтение)
    # ------------------------------------------------------------------

    @property
    def owner_id(self) -> UUID:
        """Возвращает id владельца. Агрегат всегда имеет ровно одного."""
        for m in self.members:
            if m.role == MemberRole.OWNER:
                return m.user_id
        # Защита от повреждённого агрегата (например, после загрузки из БД).
        raise RuntimeError(f"Corrupted aggregate: ShoppingList {self.id} has no owner")

    @property
    def member_ids(self) -> set[UUID]:
        return {m.user_id for m in self.members}

    def is_member(self, user_id: UUID) -> bool:
        return user_id in self.member_ids

    def is_owner(self, user_id: UUID) -> bool:
        return user_id == self.owner_id

    # ------------------------------------------------------------------
    # Управление списком (FR-13)
    # ------------------------------------------------------------------

    def rename(self, new_name: str, actor_id: UUID) -> None:
        """Переименовать список. Только владелец (FR-13)."""
        if not self.is_owner(actor_id):
            raise NotListOwnerError(self.id, actor_id)
        self.name = new_name

    # ------------------------------------------------------------------
    # Управление участниками (FR-30..36)
    # ------------------------------------------------------------------

    def invite_member(self, user_id: UUID, actor_id: UUID) -> ListMember:
        """Пригласить пользователя в список.

        FR-30: только владелец.
        FR-32: нельзя пригласить того, кто уже участник.
        """
        if not self.is_owner(actor_id):
            raise NotListOwnerError(self.id, actor_id)
        if user_id in self.member_ids:
            raise MemberAlreadyExistsError(self.id, user_id)
        member = ListMember(user_id=user_id, role=MemberRole.MEMBER)
        self.members.append(member)
        return member

    def remove_member(self, user_id: UUID, actor_id: UUID) -> None:
        """Удалить участника.

        FR-33: только владелец.
        FR-34: владелец не может удалить себя — нужно передать владение.
        """
        if not self.is_owner(actor_id):
            raise NotListOwnerError(self.id, actor_id)
        if user_id == self.owner_id:
            raise CannotRemoveOwnerError(self.id)
        if user_id not in self.member_ids:
            raise MemberNotFoundError(self.id, user_id)
        self.members = [m for m in self.members if m.user_id != user_id]

    def leave(self, user_id: UUID) -> None:
        """Участник покидает список.

        FR-36: владелец не может покинуть список.
        """
        if user_id == self.owner_id:
            raise OwnerCannotLeaveError(self.id)
        if user_id not in self.member_ids:
            raise MemberNotFoundError(self.id, user_id)
        self.members = [m for m in self.members if m.user_id != user_id]

    def transfer_ownership_to(self, new_owner_id: UUID, actor_id: UUID) -> None:
        """Передать владение другому участнику.

        FR-35: текущий владелец становится обычным участником,
        указанный пользователь становится владельцем.
        """
        if not self.is_owner(actor_id):
            raise NotListOwnerError(self.id, actor_id)
        if new_owner_id not in self.member_ids:
            raise MemberNotFoundError(self.id, new_owner_id)
        for m in self.members:
            if m.user_id == actor_id:
                m.role = MemberRole.MEMBER
            elif m.user_id == new_owner_id:
                m.role = MemberRole.OWNER

    # ------------------------------------------------------------------
    # Управление элементами (FR-21..25: владелец и участники)
    # ------------------------------------------------------------------

    def add_item(
        self, name: str, actor_id: UUID, quantity: str | None = None
    ) -> ListItem:
        """Добавить товар в список (FR-21)."""
        if not self.is_member(actor_id):
            raise NotListMemberError(self.id, actor_id)
        item = ListItem(name=name, quantity=quantity)
        self.items.append(item)
        return item

    def update_item(
        self,
        item_id: UUID,
        actor_id: UUID,
        name: str | None = None,
        quantity: str | None = None,
    ) -> ListItem:
        """Редактировать товар. None означает «оставить как есть» (FR-22)."""
        if not self.is_member(actor_id):
            raise NotListMemberError(self.id, actor_id)
        item = self._find_item(item_id)
        if name is not None:
            item.name = name
        if quantity is not None:
            item.quantity = quantity
        return item

    def mark_item_purchased(
        self, item_id: UUID, actor_id: UUID, purchased: bool = True
    ) -> ListItem:
        """Отметить товар купленным / не купленным (FR-23, FR-24)."""
        if not self.is_member(actor_id):
            raise NotListMemberError(self.id, actor_id)
        item = self._find_item(item_id)
        item.purchased = purchased
        return item

    def remove_item(self, item_id: UUID, actor_id: UUID) -> None:
        """Удалить товар из списка (FR-25)."""
        if not self.is_member(actor_id):
            raise NotListMemberError(self.id, actor_id)
        self._find_item(item_id)  # поднимает ListItemNotFoundError, если нет
        self.items = [i for i in self.items if i.id != item_id]

    def _find_item(self, item_id: UUID) -> ListItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise ListItemNotFoundError(self.id, item_id)
