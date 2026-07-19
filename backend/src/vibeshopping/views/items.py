"""HTTP-обработчики элементов списка.

Тонкий слой: парсинг DTO → вызов use case → маппинг в response DTO.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from vibeshopping.domain.shopping_list import ListItem
from vibeshopping.schemas.items import (
    ItemCreate,
    ItemUpdate,
    ListItemResponse,
    MarkPurchasedRequest,
)
from vibeshopping.views.dependencies import (
    domain_error_handler,
    get_add_item,
    get_current_user_id,
    get_delete_item,
    get_mark_item_purchased,
    get_update_item,
)

router = APIRouter(prefix="/lists/{list_id}/items", tags=["items"])


def _item_to_dto(item: ListItem) -> ListItemResponse:
    return ListItemResponse(
        id=str(item.id),
        name=item.name,
        quantity=item.quantity,
        purchased=item.purchased,
        created_at=item.created_at,
    )


@router.post("", status_code=201)
async def add_item(
    list_id: UUID,
    body: ItemCreate,
    use_case=Depends(get_add_item),
    user_id: UUID = Depends(get_current_user_id),
) -> ListItemResponse:
    """Добавить товар в список (FR-20)."""
    try:
        item = await use_case.execute(
            list_id=list_id,
            name=body.name,
            actor_id=user_id,
            quantity=body.quantity,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _item_to_dto(item)


@router.patch("/{item_id}")
async def update_item(
    list_id: UUID,
    item_id: UUID,
    body: ItemUpdate,
    use_case=Depends(get_update_item),
    user_id: UUID = Depends(get_current_user_id),
) -> ListItemResponse:
    """Редактировать товар (FR-22)."""
    try:
        item = await use_case.execute(
            list_id=list_id,
            item_id=item_id,
            actor_id=user_id,
            name=body.name,
            quantity=body.quantity,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _item_to_dto(item)


@router.patch("/{item_id}/purchased")
async def mark_item_purchased(
    list_id: UUID,
    item_id: UUID,
    body: MarkPurchasedRequest,
    use_case=Depends(get_mark_item_purchased),
    user_id: UUID = Depends(get_current_user_id),
) -> ListItemResponse:
    """Отметить товар купленным / не купленным (FR-23, FR-24)."""
    try:
        item = await use_case.execute(
            list_id=list_id,
            item_id=item_id,
            actor_id=user_id,
            purchased=body.purchased,
        )
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _item_to_dto(item)


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    list_id: UUID,
    item_id: UUID,
    use_case=Depends(get_delete_item),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Удалить товар из списка (FR-25)."""
    try:
        await use_case.execute(list_id=list_id, item_id=item_id, actor_id=user_id)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
