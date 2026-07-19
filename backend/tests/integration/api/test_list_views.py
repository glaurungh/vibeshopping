"""Интеграционные тесты для /lists endpoint'ов."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    api_client: AsyncClient, email: str = "user@example.com"
) -> str:
    """Хелпер: зарегистрировать пользователя и вернуть access_token."""
    resp = await api_client.post(
        "/auth/register",
        json={"email": email, "password": "secret12345"},
    )
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# POST /lists — создание списка
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_create_list(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    resp = await api_client.post(
        "/lists",
        json={"name": "Groceries"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Groceries"
    assert len(data["members"]) == 1
    assert data["members"][0]["role"] == "owner"
    assert len(data["items"]) == 0


@pytest.mark.integration
async def test_create_list_without_auth(api_client: AsyncClient) -> None:
    resp = await api_client.post("/lists", json={"name": "No Auth"})
    assert resp.status_code == 401


@pytest.mark.integration
async def test_create_list_rejects_empty_name(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    resp = await api_client.post(
        "/lists",
        json={"name": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /lists — список списков
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_lists_empty(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    resp = await api_client.get(
        "/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
async def test_get_lists_returns_created(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    await api_client.post(
        "/lists",
        json={"name": "List A"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await api_client.post(
        "/lists",
        json={"name": "List B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await api_client.get(
        "/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    lists = resp.json()
    assert len(lists) == 2
    names = {lst["name"] for lst in lists}
    assert names == {"List A", "List B"}


# ---------------------------------------------------------------------------
# GET /lists/{id} — детали списка
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_list_by_id(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    created = await api_client.post(
        "/lists",
        json={"name": "My List"},
        headers={"Authorization": f"Bearer {token}"},
    )
    list_id = created.json()["id"]
    resp = await api_client.get(
        f"/lists/{list_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "My List"


@pytest.mark.integration
async def test_get_list_nonexistent_returns_404(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    resp = await api_client.get(
        "/lists/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /lists/{id} — переименование
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_rename_list(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    created = await api_client.post(
        "/lists",
        json={"name": "Old Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    list_id = created.json()["id"]
    resp = await api_client.patch(
        f"/lists/{list_id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


# ---------------------------------------------------------------------------
# DELETE /lists/{id} — удаление
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_delete_list(api_client: AsyncClient) -> None:
    token = await _register_and_get_token(api_client)
    created = await api_client.post(
        "/lists",
        json={"name": "To Delete"},
        headers={"Authorization": f"Bearer {token}"},
    )
    list_id = created.json()["id"]

    resp = await api_client.delete(
        f"/lists/{list_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Проверяем, что список больше не существует
    resp2 = await api_client.get(
        f"/lists/{list_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 404
