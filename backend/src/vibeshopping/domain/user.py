"""Агрегат User.

User — анемичная модель: логика регистрации (проверка уникальности email,
хеширование пароля) вынесена в use case `RegisterUser`, поскольку требует
обращения к репозиторию и порту хеширования — инфраструктуре, от которой
домен зависеть не должен. См. docs/architecture.md, раздел «Богатые vs
анемичные модели».
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """Пользователь приложения.

    Атрибуты:
        id: уникальный идентификатор (генерируется в домене, UUID).
        email: уникальный email пользователя (FR-06).
        hashed_password: хешированный пароль (никогда не хранить открытый).
        created_at: момент создания учётной записи (UTC).
    """

    id: UUID = Field(default_factory=uuid4)
    email: EmailStr
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
