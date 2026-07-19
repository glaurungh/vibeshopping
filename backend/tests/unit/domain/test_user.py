"""Unit-тесты доменной модели User.

User — анемичная модель: логика регистрируется в use cases (RegisterUser),
поэтому здесь проверяется только структура и значения по умолчанию.
"""

from uuid import UUID

import pytest

from vibeshopping.domain.user import User


class TestUserCreation:
    """Создание пользователя."""

    def test_create_user_with_explicit_id_and_timestamps(self) -> None:
        user = User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="alice@example.com",
            hashed_password="hashed-secret",
        )

        assert user.id == UUID("00000000-0000-0000-0000-000000000001")
        assert user.email == "alice@example.com"
        assert user.hashed_password == "hashed-secret"
        assert user.created_at is not None

    def test_create_user_generates_id_by_default(self) -> None:
        user = User(email="bob@example.com", hashed_password="x")

        assert isinstance(user.id, UUID)
        # два пользователя получают разные id
        other = User(email="carol@example.com", hashed_password="y")
        assert user.id != other.id

    def test_create_user_generates_created_at_by_default(self) -> None:
        user = User(email="dave@example.com", hashed_password="x")

        assert user.created_at is not None
        # created_at должен быть осмысленным (не далеко в будущем)
        assert user.created_at.year >= 2024

    def test_invalid_email_raises_validation_error(self) -> None:
        with pytest.raises(Exception):  # pydantic.ValidationError
            User(email="not-an-email", hashed_password="x")  # type: ignore[arg-type]
