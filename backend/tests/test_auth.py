import json
import logging
from contextlib import closing
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, fetch_one, isoformat, run, transaction, utc_now
from app.main import create_app
from app.schemas import Role
from tests.support import API_BASE_URL, DEFAULT_PASSWORD, DEMO_PASSWORD, LoginAs, UserFactory

REGISTER_PAYLOAD: dict[str, Any] = {
    "username": "new.user",
    "password": "Register-Pass-2026!",
    "full_name": "New User",
    "department": "HR",
}


def login_payload(username: str, password: str = DEFAULT_PASSWORD) -> dict[str, str]:
    return {"username": username, "password": password}


def count_users(settings: Settings, username: str) -> int:
    with closing(connect(settings.database_path)) as conn:
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users WHERE username = ?", (username,))
    assert row is not None
    count: int = row["n"]
    return count


def security_events(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "patchpoint.security"
    ]


def test_register_creates_employee_account(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new.user"
    assert body["role"] == "employee"


def test_register_rejects_duplicate_username_without_database_details(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("taken")

    response = client.post("/api/auth/register", json={**REGISTER_PAYLOAD, "username": "taken"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Username is already taken"}


@pytest.mark.parametrize(
    "payload",
    [
        {key: value for key, value in REGISTER_PAYLOAD.items() if key != "username"},
        {**REGISTER_PAYLOAD, "username": "ab"},
        {**REGISTER_PAYLOAD, "username": "bad name"},
        {**REGISTER_PAYLOAD, "full_name": ""},
        {**REGISTER_PAYLOAD, "password": "x" * 14},
        {**REGISTER_PAYLOAD, "password": "x" * 129},
    ],
    ids=[
        "missing-username",
        "short-username",
        "username-with-space",
        "empty-full-name",
        "short-password",
        "long-password",
    ],
)
def test_register_validates_payload(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_role_field(client: TestClient, settings: Settings) -> None:
    response = client.post("/api/auth/register", json={**REGISTER_PAYLOAD, "role": "agent"})

    assert response.status_code == 422
    assert count_users(settings, "new.user") == 0


def test_register_enforces_password_policy(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "username": "anna.nowak", "password": "anna.nowak-long-pass"},
    )

    assert response.status_code == 422
    assert "Password must not contain the username" in response.text


def test_user_responses_never_include_password_hash(
    client: TestClient, user_factory: UserFactory
) -> None:
    registered = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    user_factory("alice")
    login = client.post("/api/auth/login", json=login_payload("alice"))
    me = client.get("/api/auth/me")

    assert registered.status_code == 201
    assert login.status_code == 200
    assert me.status_code == 200
    assert "password_hash" not in registered.json()
    assert "password_hash" not in login.json()["user"]
    assert "password_hash" not in me.json()


def test_login_then_me_returns_current_user(user_factory: UserFactory, login_as: LoginAs) -> None:
    user_factory("alice", full_name="Alice Smith")

    session_client = login_as("alice")
    response = session_client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["full_name"] == "Alice Smith"


def test_login_failures_are_indistinguishable(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")

    unknown = client.post("/api/auth/login", json=login_payload("nobody", "whatever-password"))
    wrong = client.post("/api/auth/login", json=login_payload("alice", "wrong-password"))

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid username or password"}
    assert "session" not in wrong.cookies


def test_login_returns_user_without_token(client: TestClient, user_factory: UserFactory) -> None:
    user_factory("alice")

    response = client.post("/api/auth/login", json=login_payload("alice"))

    assert response.status_code == 200
    assert set(response.json()) == {"user"}


def test_session_cookie_has_security_attributes(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")

    response = client.post("/api/auth/login", json=login_payload("alice"))

    cookie = response.headers["set-cookie"].lower()
    for attribute in ("httponly", "secure", "samesite=strict", "max-age=28800", "path=/"):
        assert attribute in cookie


def test_bearer_header_is_not_accepted(
    app: FastAPI, client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")
    client.post("/api/auth/login", json=login_payload("alice"))
    token = client.cookies.get("session")
    assert token

    with TestClient(app, base_url=API_BASE_URL) as other:
        response = other.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_login_is_blocked_after_repeated_failures(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")
    for _ in range(5):
        failed = client.post("/api/auth/login", json=login_payload("alice", "wrong-password"))
        assert failed.status_code == 401

    response = client.post("/api/auth/login", json=login_payload("alice"))

    assert response.status_code == 429
    assert response.headers["retry-after"] == "900"
    assert response.json() == {"detail": "Too many failed login attempts. Try again later."}


def test_old_login_failures_do_not_block(
    client: TestClient, settings: Settings, user_factory: UserFactory
) -> None:
    user_factory("alice")
    stale = isoformat(utc_now() - timedelta(minutes=16))
    with closing(connect(settings.database_path)) as conn, transaction(conn):
        for _ in range(5):
            run(
                conn,
                "INSERT INTO login_failures (username, attempted_at) VALUES (?, ?)",
                ("alice", stale),
            )

    response = client.post("/api/auth/login", json=login_payload("alice"))

    assert response.status_code == 200


def test_successful_login_clears_failure_count(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")
    bad = login_payload("alice", "wrong-password")

    for _ in range(4):
        assert client.post("/api/auth/login", json=bad).status_code == 401
    assert client.post("/api/auth/login", json=login_payload("alice")).status_code == 200
    for _ in range(4):
        assert client.post("/api/auth/login", json=bad).status_code == 401

    response = client.post("/api/auth/login", json=login_payload("alice"))

    assert response.status_code == 200


def test_authentication_events_are_logged_without_secrets(
    client: TestClient, user_factory: UserFactory, caplog: pytest.LogCaptureFixture
) -> None:
    user_factory("alice")
    wrong_password = "wrong-password-value"

    client.post("/api/auth/login", json=login_payload("alice", wrong_password))
    client.post("/api/auth/login", json=login_payload("alice"))

    events = security_events(caplog)
    assert [event["event"] for event in events] == ["login_failed", "login_succeeded"]
    assert events[0]["reason"] == "bad_password"
    assert events[0]["username"] == "alice"
    for record in caplog.records:
        assert wrong_password not in record.getMessage()
        assert DEFAULT_PASSWORD not in record.getMessage()


def test_registration_events_are_logged(
    client: TestClient, user_factory: UserFactory, caplog: pytest.LogCaptureFixture
) -> None:
    user_factory("taken")

    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    client.post("/api/auth/register", json={**REGISTER_PAYLOAD, "username": "taken"})

    events = security_events(caplog)
    assert [event["event"] for event in events] == ["user_registered", "registration_conflict"]
    assert events[0]["role"] == "employee"
    assert events[1]["username"] == "taken"
    assert all(REGISTER_PAYLOAD["password"] not in record.getMessage() for record in caplog.records)


def test_me_requires_session(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_forged_session_cookie(client: TestClient) -> None:
    client.cookies.set("session", "forged")

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_logout_ends_browser_session(user_factory: UserFactory, login_as: LoginAs) -> None:
    user_factory("alice")
    session_client = login_as("alice")

    logout = session_client.post("/api/auth/logout")
    me = session_client.get("/api/auth/me")

    assert logout.status_code == 200
    assert logout.json() == {"message": "Logged out"}
    assert me.status_code == 401


def test_logout_without_session_succeeds(client: TestClient) -> None:
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}


def test_demo_accounts_use_configured_password(seeded_settings: Settings) -> None:
    with TestClient(create_app(seeded_settings), base_url=API_BASE_URL) as seeded_client:
        agent = seeded_client.post("/api/auth/login", json=login_payload("helpdesk", DEMO_PASSWORD))
        employee = seeded_client.post(
            "/api/auth/login", json=login_payload("jan.kowalski", DEMO_PASSWORD)
        )
        admin = seeded_client.post("/api/auth/login", json=login_payload("admin", DEMO_PASSWORD))
        legacy = seeded_client.post(
            "/api/auth/login", json=login_payload("helpdesk", "helpdesk123")
        )

    assert agent.status_code == 200
    assert agent.json()["user"]["role"] == Role.AGENT
    assert employee.status_code == 200
    assert employee.json()["user"]["role"] == Role.EMPLOYEE
    assert admin.status_code == 401
    assert legacy.status_code == 401


def test_seeding_is_idempotent_across_restarts(seeded_settings: Settings) -> None:
    app = create_app(seeded_settings)
    with TestClient(app):
        pass
    with TestClient(app):
        pass

    with closing(connect(seeded_settings.database_path)) as conn:
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users")

    assert row is not None
    assert row["n"] == 3


def test_seeding_logs_event_once(
    seeded_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(seeded_settings)
    with caplog.at_level(logging.INFO, logger="patchpoint.security"):
        with TestClient(app):
            pass
        with TestClient(app):
            pass

    events = [event["event"] for event in security_events(caplog)]
    assert events == ["demo_data_seeded"]
