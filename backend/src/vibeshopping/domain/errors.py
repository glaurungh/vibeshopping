"""Доменные исключения VibeShopping.

Эти ошибки представляют нарушения бизнес-правил из docs/spec.md.
Они живут в домене (а не в HTTP-слое), потому что это часть языка
предметной области: «пользователь уже существует», «нельзя удалить владельца».

Use cases поднимают эти ошибки; views (HTTP-слой) маппят их в соответствующие
HTTP-статусы (403, 404, 409 и т.д.).
"""

from uuid import UUID


class DomainError(Exception):
    """Базовый класс всех доменных ошибок."""


# --- Пользователи / аутентификация ---


class UserAlreadyExistsError(DomainError):
    """FR-06: email должен быть уникальным."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User with email {email!r} already exists")


class InvalidCredentialsError(DomainError):
    """Неверный email или пароль при логине."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class UserNotFoundError(DomainError):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User with email {email!r} not found")


# --- Права доступа к списку ---


class NotListOwnerError(DomainError):
    """Только владелец может выполнять операцию (FR-13, FR-30, FR-33)."""

    def __init__(self, list_id: UUID, actor_id: UUID) -> None:
        self.list_id = list_id
        self.actor_id = actor_id
        super().__init__(f"User {actor_id} is not the owner of list {list_id}")


class NotListMemberError(DomainError):
    """Только владелец и участники могут выполнять операцию (FR-21..25)."""

    def __init__(self, list_id: UUID, actor_id: UUID) -> None:
        self.list_id = list_id
        self.actor_id = actor_id
        super().__init__(f"User {actor_id} is not a member of list {list_id}")


# --- Управление участниками ---


class MemberAlreadyExistsError(DomainError):
    """FR-32: один пользователь не может быть добавлен дважды."""

    def __init__(self, list_id: UUID, user_id: UUID) -> None:
        self.list_id = list_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is already a member of list {list_id}")


class MemberNotFoundError(DomainError):
    def __init__(self, list_id: UUID, user_id: UUID) -> None:
        self.list_id = list_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is not a member of list {list_id}")


class CannotRemoveOwnerError(DomainError):
    """FR-34: владелец не может удалить себя (нужно передать владение)."""

    def __init__(self, list_id: UUID) -> None:
        self.list_id = list_id
        super().__init__(
            f"Cannot remove the owner from list {list_id}; transfer ownership first"
        )


class OwnerCannotLeaveError(DomainError):
    """FR-36: владелец не может покинуть список."""

    def __init__(self, list_id: UUID) -> None:
        self.list_id = list_id
        super().__init__(f"Owner cannot leave list {list_id}; transfer ownership first")


# --- Элементы списка ---


class ListItemNotFoundError(DomainError):
    def __init__(self, list_id: UUID, item_id: UUID) -> None:
        self.list_id = list_id
        self.item_id = item_id
        super().__init__(f"Item {item_id} not found in list {list_id}")
