"""Pydantic DTO для элементов списка (HTTP-слой)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """POST /lists/{id}/items — добавление элемента."""

    name: str = Field(min_length=1)
    quantity: str | None = None


class ItemUpdate(BaseModel):
    """PATCH /lists/{id}/items/{item_id} — редактирование элемента."""

    name: str | None = Field(default=None, min_length=1)
    quantity: str | None = None


class MarkPurchasedRequest(BaseModel):
    """PATCH /lists/{id}/items/{item_id}/purchased."""

    purchased: bool = True


class ListItemResponse(BaseModel):
    """Ответ: элемент списка."""

    id: str
    name: str
    quantity: str | None = None
    purchased: bool = False
    created_at: datetime
