import pytest


async def _token(client, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_employee_gets_only_own_hr_metrics(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.get("/api/v1/me/hr-metrics", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "emp-001"
    assert data["leave_days_remaining"] == 8.5
    assert data["insurance_status"] == "active"
    assert data["reward_review_status"] == "in_review"


@pytest.mark.asyncio
async def test_employee_id_query_parameter_is_ignored(client):
    token = await _token(client, "employee@example.com", "employee123")

    response = await client.get(
        "/api/v1/me/hr-metrics?employee_id=hr-001",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == "emp-001"


@pytest.mark.asyncio
async def test_hr_metrics_requires_token(client):
    response = await client.get("/api/v1/me/hr-metrics")

    assert response.status_code == 401
