"""HTTP-обработчики списков покупок.

Тонкий слой: парсинг DTO → вызов use case → маппинг в response DTO.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from vibeshopping.domain.shopping_list import ListItem, ListMember, ShoppingList
from vibeshopping.schemas.lists import (
    ShoppingListCreate,
    ShoppingListResponse,
    ShoppingListSummary,
    ShoppingListUpdate,
)
from vibeshopping.views.dependencies import (
    domain_error_handler,
    get_create_list,
    get_current_user_id,
    get_delete_list,
    get_get_list,
    get_get_lists,
    get_rename_list,
)

router = APIRouter(prefix="/lists", tags=["lists"])


# ---------------------------------------------------------------------------
# Маппинг доменных моделей → DTO
# ---------------------------------------------------------------------------


def _member_to_dto(m: ListMember) -> dict[str, object]:
    return {
        "user_id": str(m.user_id),
        "role": m.role.value,
    }


def _item_to_dto(i: ListItem) -> dict[str, object]:
    return {
        "id": str(i.id),
        "name": i.name,
        "quantity": i.quantity,
        "purchased": i.purchased,
    }


def _list_to_response(lst: ShoppingList) -> ShoppingListResponse:
    return ShoppingListResponse(
        id=str(lst.id),
        name=lst.name,
        members=[_member_to_dto(m) for m in lst.members],  # type: ignore[arg-type]
        items=[_item_to_dto(i) for i in lst.items],  # type: ignore[arg-type]
        created_at=lst.created_at,
    )


def _list_to_summary(lst: ShoppingList) -> ShoppingListSummary:
    return ShoppingListSummary(
        id=str(lst.id),
        name=lst.name,
        created_at=lst.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_list(
    body: ShoppingListCreate,
    use_case=Depends(get_create_list),
    user_id: UUID = Depends(get_current_user_id),
) -> ShoppingListResponse:
    """Создать список покупок (FR-10, FR-11)."""
    try:
        lst = await use_case.execute(name=body.name, owner_id=user_id)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _list_to_response(lst)


@router.get("")
async def get_lists(
    use_case=Depends(get_get_lists),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ShoppingListSummary]:
    """Все списки пользователя (FR-12)."""
    lists = await use_case.execute(user_id=user_id)
    return [_list_to_summary(lst) for lst in lists]


@router.get("/{list_id}")
async def get_list(
    list_id: UUID,
    use_case=Depends(get_get_list),
    user_id: UUID = Depends(get_current_user_id),
) -> ShoppingListResponse:
    """Получить один список с участниками и элементами (FR-12)."""
    try:
        lst = await use_case.execute(list_id=list_id, actor_id=user_id)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _list_to_response(lst)


@router.patch("/{list_id}")
async def rename_list(
    list_id: UUID,
    body: ShoppingListUpdate,
    use_case=Depends(get_rename_list),
    user_id: UUID = Depends(get_current_user_id),
) -> ShoppingListResponse:
    """Переименовать список (FR-13)."""
    try:
        lst = await use_case.execute(
            list_id=list_id, new_name=body.name, actor_id=user_id
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _list_to_response(lst)


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: UUID,
    use_case=Depends(get_delete_list),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Удалить список со всем содержимым (FR-13, FR-14)."""
    try:
        await use_case.execute(list_id=list_id, actor_id=user_id)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
