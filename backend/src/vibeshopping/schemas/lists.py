"""Pydantic DTO для списков покупок (HTTP-слой)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ShoppingListCreate(BaseModel):
    """POST /lists — создание списка."""

    name: str = Field(min_length=1)


class ShoppingListUpdate(BaseModel):
    """PATCH /lists/{id} — переименование."""

    name: str = Field(min_length=1)


class ListMemberResponse(BaseModel):
    """Участник списка (вложенный DTO)."""

    user_id: str  # UUID as string for JSON serialization
    role: str


class ListItemResponse(BaseModel):
    """Элемент списка (вложенный DTO)."""

    id: str
    name: str
    quantity: str | None = None
    purchased: bool = False


class ShoppingListResponse(BaseModel):
    """Ответ: список покупок с участниками и элементами."""

    id: str
    name: str
    members: list[ListMemberResponse]
    items: list[ListItemResponse]
    created_at: datetime


class ShoppingListSummary(BaseModel):
    """Краткий DTO для списка в GET /lists."""

    id: str
    name: str
    created_at: datetime
