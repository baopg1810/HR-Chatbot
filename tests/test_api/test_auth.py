import pytest


@pytest.mark.asyncio
async def test_login_returns_token_and_user(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["role"] == "employee"


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    token = login_response.json()["access_token"]

    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "employee@example.com"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_and_new_access_token_works(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    old_refresh_token = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert refresh_response.status_code == 200
    token_data = refresh_response.json()
    assert token_data["access_token"]
    assert token_data["refresh_token"]
    assert token_data["refresh_token"] != old_refresh_token

    me_response = await client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "employee@example.com"

    reused_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert reused_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access_token(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200
    assert logout_response.json()["ok"] is True

    refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
