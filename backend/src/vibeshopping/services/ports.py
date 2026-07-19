"""Порты приложения (application ports).

Интерфейсы инфраструктурных зависимостей, в которых нуждаются use cases,
но которые не должны жить в домене (потому что это чисто технические
механизмы — хеширование паролей, выпуск JWT). Use cases зависят от этих
Protocol-ов; конкретные реализации (BcryptPasswordHasher, JoseTokenService)
живут в `infrastructure/security/`.

См. docs/architecture.md, раздел «Dependency Inversion».
"""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class PasswordHasher(Protocol):
    """Хеширование и проверка паролей (FR-02)."""

    def hash(self, password: str) -> str:
        """Вернуть хеш пароля."""
        ...

    def verify(self, password: str, hashed: str) -> bool:
        """Проверить пароль против хеша."""
        ...


@runtime_checkable
class TokenService(Protocol):
    """Выпуск и проверка JWT-токенов (FR-03, FR-04, FR-05)."""

    def create_access_token(self, user_id: UUID) -> str:
        """Выпустить access-токен (короткий срок)."""
        ...

    def create_refresh_token(self, user_id: UUID) -> str:
        """Выпустить refresh-токен (длинный срок)."""
        ...

    def decode_user_id(self, token: str) -> UUID | None:
        """Извлечь user_id из токена. None если невалиден или истёк."""
        ...
