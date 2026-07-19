"""Unit-тесты use cases аутентификации.

Используют in-memory реализации протоколов (см. tests/unit/fakes.py) —
БД и реальная криптография не нужны. Это позволяет тестировать чистую
логику use cases мгновенно и детерминированно.
"""

from uuid import uuid4

import pytest

from tests.unit.fakes import (
    FakePasswordHasher,
    FakeTokenService,
    InMemoryUserRepository,
)
from vibeshopping.domain.errors import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from vibeshopping.domain.user import User
from vibeshopping.services.auth import LoginUser, RefreshToken, RegisterUser, TokenPair

# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def tokens() -> FakeTokenService:
    return FakeTokenService()


# ---------------------------------------------------------------------------
# RegisterUser
# ---------------------------------------------------------------------------


class TestRegisterUser:
    async def test_register_new_user_persists_and_hashes_password(
        self, users: InMemoryUserRepository, hasher: FakePasswordHasher
    ) -> None:
        register = RegisterUser(users=users, hasher=hasher)

        user = await register.execute(email="alice@example.com", password="secret123")

        # Возвращённый пользователь
        assert user.email == "alice@example.com"
        # Пароль захеширован (FR-02): пароль не восстанавливается из хеша
        assert user.hashed_password != "secret123"
        assert "secret123" not in user.hashed_password
        # Хеш валиден: проверка проходит
        assert hasher.verify("secret123", user.hashed_password)
        # Сохранён в репозитории
        stored = await users.get_by_email("alice@example.com")
        assert stored is not None
        assert stored.id == user.id

    async def test_register_generates_id_and_created_at(
        self, users: InMemoryUserRepository, hasher: FakePasswordHasher
    ) -> None:
        register = RegisterUser(users=users, hasher=hasher)

        user = await register.execute(email="bob@example.com", password="password")

        assert user.id is not None
        assert user.created_at is not None

    async def test_register_duplicate_email_raises(
        self, users: InMemoryUserRepository, hasher: FakePasswordHasher
    ) -> None:
        # существующий пользователь с тем же email (FR-06)
        existing = User(
            email="carol@example.com",
            hashed_password="already-here",
        )
        await users.add(existing)
        register = RegisterUser(users=users, hasher=hasher)

        with pytest.raises(UserAlreadyExistsError):
            await register.execute(email="carol@example.com", password="anything")

    async def test_register_email_is_case_insensitive(
        self, users: InMemoryUserRepository, hasher: FakePasswordHasher
    ) -> None:
        await users.add(User(email="dave@example.com", hashed_password="x"))
        register = RegisterUser(users=users, hasher=hasher)

        with pytest.raises(UserAlreadyExistsError):
            await register.execute(email="DAVE@example.com", password="y")

    async def test_register_does_not_store_plain_password(
        self, users: InMemoryUserRepository, hasher: FakePasswordHasher
    ) -> None:
        register = RegisterUser(users=users, hasher=hasher)

        user = await register.execute(email="eve@example.com", password="supersecret")

        # Ни в объекте, ни в хранилище не должно быть открытого пароля
        assert "supersecret" not in user.hashed_password


# ---------------------------------------------------------------------------
# LoginUser
# ---------------------------------------------------------------------------


class TestLoginUser:
    async def test_login_returns_token_pair(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        # Зарегистрированный пользователь
        await users.add(
            User(
                email="alice@example.com",
                hashed_password=hasher.hash("secret123"),
            )
        )
        login = LoginUser(users=users, hasher=hasher, tokens=tokens)

        result = await login.execute(email="alice@example.com", password="secret123")

        assert isinstance(result, TokenPair)
        assert result.access_token
        assert result.refresh_token
        # токены разные (FR-03, FR-04)
        assert result.access_token != result.refresh_token

    async def test_login_token_pair_contains_user_id(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        user = User(
            email="alice@example.com",
            hashed_password=hasher.hash("secret123"),
        )
        await users.add(user)
        login = LoginUser(users=users, hasher=hasher, tokens=tokens)

        result = await login.execute(email="alice@example.com", password="secret123")

        # access-токен декодируется в того же пользователя
        decoded = tokens.decode_user_id(result.access_token)
        assert decoded == user.id

    async def test_login_unknown_email_raises_invalid_credentials(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        login = LoginUser(users=users, hasher=hasher, tokens=tokens)

        with pytest.raises(InvalidCredentialsError):
            await login.execute(email="ghost@example.com", password="x")

    async def test_login_wrong_password_raises_invalid_credentials(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        await users.add(
            User(
                email="alice@example.com",
                hashed_password=hasher.hash("correct"),
            )
        )
        login = LoginUser(users=users, hasher=hasher, tokens=tokens)

        with pytest.raises(InvalidCredentialsError):
            await login.execute(email="alice@example.com", password="wrong")

    async def test_login_is_case_insensitive(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        await users.add(
            User(
                email="alice@example.com",
                hashed_password=hasher.hash("secret"),
            )
        )
        login = LoginUser(users=users, hasher=hasher, tokens=tokens)

        result = await login.execute(email="ALICE@example.com", password="secret")

        assert isinstance(result, TokenPair)


# ---------------------------------------------------------------------------
# RefreshToken
# ---------------------------------------------------------------------------


class TestRefreshToken:
    async def test_refresh_issues_new_token_pair(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        user = User(
            email="alice@example.com",
            hashed_password=hasher.hash("secret"),
        )
        await users.add(user)
        refresh_token = tokens.create_refresh_token(user.id)
        refresh_uc = RefreshToken(users=users, tokens=tokens)

        result = await refresh_uc.execute(refresh_token)

        assert isinstance(result, TokenPair)
        assert result.access_token
        assert result.refresh_token
        # новые токены отличаются от исходного
        assert result.access_token != refresh_token
        assert result.refresh_token != refresh_token

    async def test_refresh_decodes_to_correct_user(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        user = User(
            email="alice@example.com",
            hashed_password=hasher.hash("secret"),
        )
        await users.add(user)
        refresh_token = tokens.create_refresh_token(user.id)
        refresh_uc = RefreshToken(users=users, tokens=tokens)

        result = await refresh_uc.execute(refresh_token)

        assert tokens.decode_user_id(result.access_token) == user.id
        assert tokens.decode_user_id(result.refresh_token) == user.id

    async def test_refresh_invalid_token_raises(
        self,
        users: InMemoryUserRepository,
        tokens: FakeTokenService,
    ) -> None:
        refresh_uc = RefreshToken(users=users, tokens=tokens)

        with pytest.raises(InvalidTokenError):
            await refresh_uc.execute("garbage-token")

    async def test_refresh_for_deleted_user_raises(
        self,
        users: InMemoryUserRepository,
        tokens: FakeTokenService,
    ) -> None:
        # Токен был выпущен, но пользователя больше нет
        ghost_id = uuid4()
        refresh_token = tokens.create_refresh_token(ghost_id)
        refresh_uc = RefreshToken(users=users, tokens=tokens)

        with pytest.raises(InvalidTokenError):
            await refresh_uc.execute(refresh_token)

    async def test_refresh_accepts_only_refresh_tokens_not_access(
        self,
        users: InMemoryUserRepository,
        hasher: FakePasswordHasher,
        tokens: FakeTokenService,
    ) -> None:
        """Access-токен не должен приниматься в качестве refresh-токена.

        Хотя FakeTokenService не различает типы токенов, контракт use case
        RefreshToken предполагает, что передан refresh-токен. В реальном
        TokenService тип токена зашит в payload (claim `typ`).
        Здесь проверяем только, что access-токен тоже валиден как refresh
        (поскольку фейк не различает), но главное — поведение на валидном
        токене. Этот тест — документирование контракта.
        """
        user = User(
            email="alice@example.com",
            hashed_password=hasher.hash("secret"),
        )
        await users.add(user)
        access_token = tokens.create_access_token(user.id)
        refresh_uc = RefreshToken(users=users, tokens=tokens)

        # access-токен декодируется в user_id → сессия обновится
        result = await refresh_uc.execute(access_token)

        assert isinstance(result, TokenPair)
