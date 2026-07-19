"""Use cases аутентификации.

Каждый use case — класс с одним методом `execute(...)`. Зависимости
(репозитории, порты) внедряются через конструктор, что позволяет в тестах
подставлять in-memory реализации (Dependency Inversion).

Покрытые требования (см. docs/spec.md):
    - FR-02: пароли хранятся в хешированном виде.
    - FR-03: access-токен (короткий срок).
    - FR-04: refresh-токен (длинный срок).
    - FR-05: обновление access-токена через refresh.
    - FR-06: email уникален.
    - FR-07: пароль ≥ 8 символов (валидация — на уровне DTO, не здесь).
"""

from dataclasses import dataclass

from vibeshopping.domain.errors import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from vibeshopping.domain.repositories import UserRepository
from vibeshopping.domain.user import User
from vibeshopping.services.ports import PasswordHasher, TokenService


@dataclass(frozen=True)
class TokenPair:
    """Результат успешного логина/refresh: пара токенов (FR-03, FR-04)."""

    access_token: str
    refresh_token: str


class RegisterUser:
    """Регистрация нового пользователя (FR-01, FR-02, FR-06)."""

    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, email: str, password: str) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)
        user = User(
            email=email,
            hashed_password=self._hasher.hash(password),
        )
        return await self._users.add(user)


class LoginUser:
    """Аутентификация по email и паролю (FR-02, FR-03, FR-04)."""

    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError()
        if not self._hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError()
        return TokenPair(
            access_token=self._tokens.create_access_token(user.id),
            refresh_token=self._tokens.create_refresh_token(user.id),
        )


class RefreshToken:
    """Обновление пары токенов по refresh-токену (FR-05)."""

    def __init__(self, users: UserRepository, tokens: TokenService) -> None:
        self._users = users
        self._tokens = tokens

    async def execute(self, refresh_token: str) -> TokenPair:
        user_id = self._tokens.decode_user_id(refresh_token)
        if user_id is None:
            raise InvalidTokenError()
        user = await self._users.get_by_id(user_id)
        if user is None:
            # Токен был выпущен, но пользователя больше нет
            raise InvalidTokenError()
        return TokenPair(
            access_token=self._tokens.create_access_token(user.id),
            refresh_token=self._tokens.create_refresh_token(user.id),
        )
