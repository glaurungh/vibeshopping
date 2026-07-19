"""Интеграционные тесты для /auth endpoint'ов.

Тестируем полный HTTP-цикл через httpx.AsyncClient с реальной БД.
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_register_returns_tokens(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "secret12345"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.integration
async def test_register_rejects_duplicate_email(api_client: AsyncClient) -> None:
    payload = {"email": "bob@example.com", "password": "secret12345"}
    resp1 = await api_client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await api_client.post("/auth/register", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


@pytest.mark.integration
async def test_register_rejects_short_password(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/auth/register",
        json={"email": "charlie@example.com", "password": "short"},
    )
    assert resp.status_code == 422  # Validation error


@pytest.mark.integration
async def test_register_rejects_invalid_email(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "secret12345"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_login_returns_tokens(api_client: AsyncClient) -> None:
    # Сначала регистрируем
    await api_client.post(
        "/auth/register",
        json={"email": "dave@example.com", "password": "secret12345"},
    )
    # Теперь логинимся
    resp = await api_client.post(
        "/auth/login",
        json={"email": "dave@example.com", "password": "secret12345"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.integration
async def test_login_rejects_wrong_password(api_client: AsyncClient) -> None:
    await api_client.post(
        "/auth/register",
        json={"email": "eve@example.com", "password": "secret12345"},
    )
    resp = await api_client.post(
        "/auth/login",
        json={"email": "eve@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_login_rejects_unknown_email(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "secret12345"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_refresh_returns_new_tokens(api_client: AsyncClient) -> None:
    reg = await api_client.post(
        "/auth/register",
        json={"email": "frank@example.com", "password": "secret12345"},
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Новый access-токен (refresh-токен может совпадать, если exp одинаковый)
    assert "access_token" in data
    assert len(data["access_token"]) > 0


@pytest.mark.integration
async def test_refresh_rejects_invalid_token(api_client: AsyncClient) -> None:
    resp = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Bearer token authentication
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_protected_endpoint_rejects_no_token(api_client: AsyncClient) -> None:
    resp = await api_client.get("/lists")
    assert resp.status_code == 401  # HTTPBearer returns 401 when no header


@pytest.mark.integration
async def test_protected_endpoint_accepts_valid_token(api_client: AsyncClient) -> None:
    reg = await api_client.post(
        "/auth/register",
        json={"email": "grace@example.com", "password": "secret12345"},
    )
    token = reg.json()["access_token"]

    resp = await api_client.get(
        "/lists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
async def test_protected_endpoint_rejects_invalid_token(
    api_client: AsyncClient,
) -> None:
    resp = await api_client.get(
        "/lists",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401
