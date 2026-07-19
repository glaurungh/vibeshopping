"""Pydantic DTO для участников списка (HTTP-слой)."""

from datetime import datetime

from pydantic import BaseModel


class InviteMemberRequest(BaseModel):
    """POST /lists/{id}/members — приглашение участника."""

    email: str


class TransferOwnershipRequest(BaseModel):
    """POST /lists/{id}/transfer-ownership — передача владения."""

    new_owner_id: str


class ListMemberResponse(BaseModel):
    """Ответ: участник списка."""

    user_id: str
    role: str
    joined_at: datetime
