"""Composition root: FastAPI Depends wiring.

Здесь все зависимости собираются вместе — это единственное место, где
инфраструктура (БД, JWT, bcrypt) связывается с use cases и views.

Views получают готовые use cases через Depends(get_...), не зная о деталях
реализации. В тестах зависимости можно подменить через override_dependency.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from vibeshopping.domain.errors import (
    CannotRemoveOwnerError,
    DomainError,
    InvalidCredentialsError,
    InvalidTokenError,
    ListItemNotFoundError,
    ListNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    NotListMemberError,
    NotListOwnerError,
    OwnerCannotLeaveError,
    UserAlreadyExistsError,
)
from vibeshopping.domain.repositories import (
    ShoppingListRepository,
    UserRepository,
)
from vibeshopping.infrastructure.db import get_session
from vibeshopping.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from vibeshopping.infrastructure.security.token_service import (
    JoseTokenService,
)
from vibeshopping.repos.shopping_list_repository import (
    SqlAlchemyShoppingListRepository,
)
from vibeshopping.repos.user_repository import SqlAlchemyUserRepository
from vibeshopping.services.auth import (
    LoginUser,
    RefreshToken,
    RegisterUser,
)
from vibeshopping.services.items import (
    AddItem,
    DeleteItem,
    MarkItemPurchased,
    UpdateItem,
)
from vibeshopping.services.lists import (
    CreateList,
    DeleteList,
    GetList,
    GetLists,
    RenameList,
)
from vibeshopping.services.members import (
    InviteMember,
    LeaveList,
    RemoveMember,
    TransferOwnership,
)
from vibeshopping.services.ports import PasswordHasher, TokenService

# ---------------------------------------------------------------------------
# Infrastructure singletons
# ---------------------------------------------------------------------------

_bearer = HTTPBearer()
_password_hasher: PasswordHasher = BcryptPasswordHasher()
_token_service: TokenService = JoseTokenService()


# ---------------------------------------------------------------------------
# Session → Repository wiring
# ---------------------------------------------------------------------------


def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_list_repo(
    session: AsyncSession = Depends(get_session),
) -> ShoppingListRepository:
    return SqlAlchemyShoppingListRepository(session)


# ---------------------------------------------------------------------------
# Use case factories
# ---------------------------------------------------------------------------


def get_register_user(
    repo: UserRepository = Depends(get_user_repo),
    hasher: PasswordHasher = Depends(lambda: _password_hasher),
) -> RegisterUser:
    return RegisterUser(users=repo, hasher=hasher)


def get_login_user(
    repo: UserRepository = Depends(get_user_repo),
    hasher: PasswordHasher = Depends(lambda: _password_hasher),
    tokens: TokenService = Depends(lambda: _token_service),
) -> LoginUser:
    return LoginUser(users=repo, hasher=hasher, tokens=tokens)


def get_refresh_token(
    repo: UserRepository = Depends(get_user_repo),
    tokens: TokenService = Depends(lambda: _token_service),
) -> RefreshToken:
    return RefreshToken(users=repo, tokens=tokens)


def get_create_list(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> CreateList:
    return CreateList(repo=repo)


def get_get_lists(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> GetLists:
    return GetLists(repo=repo)


def get_get_list(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> GetList:
    return GetList(repo=repo)


def get_rename_list(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> RenameList:
    return RenameList(repo=repo)


def get_delete_list(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> DeleteList:
    return DeleteList(repo=repo)


def get_add_item(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> AddItem:
    return AddItem(repo=repo)


def get_update_item(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> UpdateItem:
    return UpdateItem(repo=repo)


def get_mark_item_purchased(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> MarkItemPurchased:
    return MarkItemPurchased(repo=repo)


def get_delete_item(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> DeleteItem:
    return DeleteItem(repo=repo)


def get_invite_member(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> InviteMember:
    return InviteMember(repo=repo)


def get_remove_member(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> RemoveMember:
    return RemoveMember(repo=repo)


def get_leave_list(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> LeaveList:
    return LeaveList(repo=repo)


def get_transfer_ownership(
    repo: ShoppingListRepository = Depends(get_list_repo),
) -> TransferOwnership:
    return TransferOwnership(repo=repo)


# ---------------------------------------------------------------------------
# Current user resolver (JWT Bearer)
# ---------------------------------------------------------------------------


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    repo: UserRepository = Depends(get_user_repo),
    tokens: TokenService = Depends(lambda: _token_service),
) -> UUID:
    """Извлечь user_id из JWT access-токена (Bearer).

    Используется как Depends в endpoint'ах, требующих аутентификации.
    Если токен невалиден или пользователь не найден — 401.
    """
    user_id = tokens.decode_user_id(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user.id


# ---------------------------------------------------------------------------
# Domain error → HTTP status mapping
# ---------------------------------------------------------------------------

_DOMAIN_ERROR_MAP: dict[type[DomainError], tuple[int, str]] = {
    UserAlreadyExistsError: (status.HTTP_409_CONFLICT, "User already exists"),
    InvalidCredentialsError: (
        status.HTTP_401_UNAUTHORIZED,
        "Invalid email or password",
    ),
    InvalidTokenError: (
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired refresh token",
    ),
    ListNotFoundError: (status.HTTP_404_NOT_FOUND, "List not found"),
    NotListOwnerError: (status.HTTP_403_FORBIDDEN, "Only the owner can do this"),
    NotListMemberError: (
        status.HTTP_403_FORBIDDEN,
        "Only list members can do this",
    ),
    MemberAlreadyExistsError: (
        status.HTTP_409_CONFLICT,
        "User is already a member of this list",
    ),
    MemberNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "User is not a member of this list",
    ),
    CannotRemoveOwnerError: (
        status.HTTP_403_FORBIDDEN,
        "Cannot remove the owner; transfer ownership first",
    ),
    OwnerCannotLeaveError: (
        status.HTTP_403_FORBIDDEN,
        "Owner cannot leave the list; transfer ownership first",
    ),
    ListItemNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "Item not found in this list",
    ),
}


def domain_error_handler(exc: DomainError) -> HTTPException:
    """Маппить доменную ошибку в HTTPException."""
    error_info = _DOMAIN_ERROR_MAP.get(type(exc))
    if error_info is None:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    http_status, detail = error_info
    return HTTPException(status_code=http_status, detail=detail)
