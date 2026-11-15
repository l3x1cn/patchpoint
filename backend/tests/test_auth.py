from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, fetch_one
from app.main import create_app
from app.schemas import Role

REGISTER_PAYLOAD: dict[str, Any] = {
    "username": "new.user",
    "password": "Secret123!",
    "full_name": "New User",
    "department": "HR",
}


@pytest.fixture
def seeded_settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "seeded.db", seed_demo_data=True)


def test_register_creates_employee_account(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new.user"
    assert body["role"] == "employee"


def test_register_rejects_duplicate_username(
    client: TestClient, user_factory: Callable[..., int]
) -> None:
    user_factory("taken")

    response = client.post("/api/auth/register", json={**REGISTER_PAYLOAD, "username": "taken"})

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {key: value for key, value in REGISTER_PAYLOAD.items() if key != "username"},
        {**REGISTER_PAYLOAD, "username": "ab"},
        {**REGISTER_PAYLOAD, "full_name": ""},
    ],
    ids=["missing-username", "short-username", "empty-full-name"],
)
def test_register_validates_payload(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422


def test_login_then_me_returns_current_user(
    user_factory: Callable[..., int], login_as: Callable[..., TestClient]
) -> None:
    user_factory("alice", full_name="Alice Smith")

    session_client = login_as("alice")
    response = session_client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["full_name"] == "Alice Smith"


def test_login_with_wrong_password_is_rejected(
    client: TestClient, user_factory: Callable[..., int]
) -> None:
    user_factory("alice")

    response = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    assert response.status_code == 401
    assert "session" not in response.cookies


def test_me_requires_session(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_forged_session_cookie(client: TestClient) -> None:
    client.cookies.set("session", "forged")

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_logout_ends_browser_session(
    user_factory: Callable[..., int], login_as: Callable[..., TestClient]
) -> None:
    user_factory("alice")
    session_client = login_as("alice")

    logout = session_client.post("/api/auth/logout")
    me = session_client.get("/api/auth/me")

    assert logout.status_code == 200
    assert logout.json() == {"message": "Logged out"}
    assert me.status_code == 401


def test_demo_accounts_can_log_in(seeded_settings: Settings) -> None:
    with TestClient(create_app(seeded_settings)) as seeded_client:
        employee = seeded_client.post(
            "/api/auth/login", json={"username": "jan.kowalski", "password": "password123"}
        )
        agent = seeded_client.post(
            "/api/auth/login", json={"username": "helpdesk", "password": "helpdesk123"}
        )

    assert employee.status_code == 200
    assert employee.json()["user"]["role"] == Role.EMPLOYEE
    assert agent.status_code == 200
    assert agent.json()["user"]["role"] == Role.AGENT


def test_seeding_is_idempotent_across_restarts(seeded_settings: Settings) -> None:
    app = create_app(seeded_settings)
    with TestClient(app):
        pass
    with TestClient(app):
        pass

    with closing(connect(seeded_settings.database_path)) as conn:
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users")

    assert row is not None
    assert row["n"] == 4
