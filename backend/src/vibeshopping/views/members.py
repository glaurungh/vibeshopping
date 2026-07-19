"""HTTP-обработчики участников списка.

Тонкий слой: парсинг DTO → вызов use case → маппинг в response DTO.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from vibeshopping.domain.shopping_list import ListMember
from vibeshopping.domain.user import User
from vibeshopping.schemas.members import (
    InviteMemberRequest,
    ListMemberResponse,
    TransferOwnershipRequest,
)
from vibeshopping.views.dependencies import (
    domain_error_handler,
    get_current_user_id,
    get_invite_member,
    get_leave_list,
    get_remove_member,
    get_transfer_ownership,
    get_user_repo,
)

router = APIRouter(prefix="/lists/{list_id}/members", tags=["members"])


def _member_to_dto(m: ListMember) -> ListMemberResponse:
    return ListMemberResponse(
        user_id=str(m.user_id),
        role=m.role.value,
        joined_at=m.joined_at,
    )


@router.post("/invite", status_code=201)
async def invite_member(
    list_id: UUID,
    body: InviteMemberRequest,
    use_case=Depends(get_invite_member),
    user_id: UUID = Depends(get_current_user_id),
    users=Depends(get_user_repo),
) -> ListMemberResponse:
    """Пригласить пользователя в список по email (FR-30, FR-32)."""
    # Ищем пользователя по email для получения user_id
    target_user: User | None = await users.get_by_email(body.email)
    if target_user is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )
    try:
        member = await use_case.execute(
            list_id=list_id,
            user_id=target_user.id,
            actor_id=user_id,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _member_to_dto(member)


@router.delete("/{user_id}", status_code=204)
async def remove_member(
    list_id: UUID,
    user_id: UUID,
    use_case=Depends(get_remove_member),
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Удалить участника из списка (FR-33, FR-34)."""
    try:
        await use_case.execute(
            list_id=list_id,
            user_id=user_id,
            actor_id=current_user_id,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]


@router.post("/leave", status_code=204)
async def leave_list(
    list_id: UUID,
    use_case=Depends(get_leave_list),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Покинуть список (FR-36)."""
    try:
        await use_case.execute(list_id=list_id, user_id=user_id)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]


@router.post("/transfer-ownership", status_code=204)
async def transfer_ownership(
    list_id: UUID,
    body: TransferOwnershipRequest,
    use_case=Depends(get_transfer_ownership),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Передать владение другому участнику (FR-35)."""
    try:
        await use_case.execute(
            list_id=list_id,
            new_owner_id=UUID(body.new_owner_id),
            actor_id=user_id,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
