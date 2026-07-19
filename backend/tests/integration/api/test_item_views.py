"""Интеграционные тесты для /lists/{id}/items endpoint'ов."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    api_client: AsyncClient, email: str = "user@example.com"
) -> str:
    resp = await api_client.post(
        "/auth/register",
        json={"email": email, "password": "secret12345"},
    )
    return resp.json()["access_token"]


async def _create_list(
    api_client: AsyncClient, token: str, name: str = "Test List"
) -> str:
    resp = await api_client.post(
        "/lists",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# POST /lists/{id}/items — добавление элемента
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_add_item(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    resp = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Milk", "quantity": "2 liters"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Milk"
    assert data["quantity"] == "2 liters"
    assert data["purchased"] is False


@pytest.mark.integration
async def test_add_item_without_quantity(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    resp = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Bread"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["quantity"] is None


@pytest.mark.integration
async def test_add_item_to_nonexistent_list_returns_404(
    api_client: AsyncClient,
) -> None:
    token = await _register_and_get_token(api_client)
    resp = await api_client.post(
        "/lists/00000000-0000-0000-0000-000000000000/items",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /lists/{id}/items/{item_id} — редактирование
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_update_item(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    created = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Eggs", "quantity": "10"},
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = created.json()["id"]

    resp = await api_client.patch(
        f"/lists/{list_id}/items/{item_id}",
        json={"name": "Organic Eggs", "quantity": "12"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Organic Eggs"
    assert data["quantity"] == "12"


# ---------------------------------------------------------------------------
# PATCH /lists/{id}/items/{item_id}/purchased — отметка купленного
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_mark_item_purchased(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    created = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Sugar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = created.json()["id"]

    resp = await api_client.patch(
        f"/lists/{list_id}/items/{item_id}/purchased",
        json={"purchased": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["purchased"] is True


@pytest.mark.integration
async def test_mark_item_not_purchased(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    created = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Salt"},
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = created.json()["id"]

    # Сначала отметим купленным
    await api_client.patch(
        f"/lists/{list_id}/items/{item_id}/purchased",
        json={"purchased": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Затем не купленным
    resp = await api_client.patch(
        f"/lists/{list_id}/items/{item_id}/purchased",
        json={"purchased": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["purchased"] is False


# ---------------------------------------------------------------------------
# DELETE /lists/{id}/items/{item_id} — удаление элемента
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_delete_item(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    list_id = await _create_list(api_client, token)

    created = await api_client.post(
        f"/lists/{list_id}/items",
        json={"name": "Trash"},
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = created.json()["id"]

    resp = await api_client.delete(
        f"/lists/{list_id}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
