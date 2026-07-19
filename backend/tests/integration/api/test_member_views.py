"""Интеграционные тесты для /lists/{id}/members endpoint'ов."""

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
# POST /lists/{id}/members/invite — приглашение
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_invite_member(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner@example.com")
    await _register_and_get_token(api_client, "member@example.com")
    list_id = await _create_list(api_client, owner_token)

    resp = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "member@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "member"


@pytest.mark.integration
async def test_invite_member_not_found_email(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner2@example.com")
    list_id = await _create_list(api_client, owner_token)

    resp = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "nonexistent@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_invite_duplicate_member_returns_409(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner3@example.com")
    await _register_and_get_token(api_client, "dup@example.com")
    list_id = await _create_list(api_client, owner_token)

    # Первый раз — успешно
    resp1 = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "dup@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp1.status_code == 201

    # Второй раз — 409
    resp2 = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "dup@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp2.status_code == 409


@pytest.mark.integration
async def test_invite_member_by_non_owner_returns_403(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner4@example.com")
    member_token = await _register_and_get_token(api_client, "mem4@example.com")
    list_id = await _create_list(api_client, owner_token)

    # Сначала пригласим mem4
    await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "mem4@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Теперь mem4 пробует пригласить другого (не может — не владелец)
    await _register_and_get_token(api_client, "third@example.com")
    resp = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "third@example.com"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /lists/{id}/members/{user_id} — удаление участника
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_remove_member(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner5@example.com")
    await _register_and_get_token(api_client, "mem5@example.com")
    list_id = await _create_list(api_client, owner_token)

    invite = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "mem5@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_user_id = invite.json()["user_id"]

    resp = await api_client.delete(
        f"/lists/{list_id}/members/{member_user_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# POST /lists/{id}/members/leave — покинуть список
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_leave_list(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner6@example.com")
    member_token = await _register_and_get_token(api_client, "mem6@example.com")
    list_id = await _create_list(api_client, owner_token)

    await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "mem6@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    resp = await api_client.post(
        f"/lists/{list_id}/members/leave",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# POST /lists/{id}/members/transfer-ownership — передача владения
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_transfer_ownership(api_client: AsyncClient) -> None:
    owner_token = await _register_and_get_token(api_client, "owner7@example.com")
    member_token = await _register_and_get_token(api_client, "mem7@example.com")
    list_id = await _create_list(api_client, owner_token)

    invite = await api_client.post(
        f"/lists/{list_id}/members/invite",
        json={"email": "mem7@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_user_id = invite.json()["user_id"]

    resp = await api_client.post(
        f"/lists/{list_id}/members/transfer-ownership",
        json={"new_owner_id": member_user_id},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 204

    # Проверяем: mem7 теперь владелец (может переименовать)
    rename = await api_client.patch(
        f"/lists/{list_id}",
        json={"name": "Renamed by new owner"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert rename.status_code == 200
