"""Pydantic DTO для аутентификации (HTTP-слой).

Request body и response body для API endpoint'ов. Отдельные от доменных
моделей — по Dependency Rule views→schemas, а не domain→schemas.
"""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """POST /auth/register — запрос на регистрацию."""

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """POST /auth/login — запрос на вход."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Ответ с парой токенов (FR-03, FR-04)."""

    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    """POST /auth/refresh — запрос на обновление токенов."""

    refresh_token: str
