from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.support import API_BASE_URL, DEFAULT_PASSWORD, UserFactory

HOST_COOKIE = "__Host-session"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "test.db", cookie_name=HOST_COOKIE)


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200

    return response.headers["set-cookie"]


def test_login_sets_host_prefixed_cookie_without_domain(
    client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")

    set_cookie = login(client, "alice")

    assert set_cookie.startswith(f"{HOST_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Secure" in set_cookie
    assert "domain=" not in set_cookie.lower()


def test_host_prefixed_cookie_authenticates_until_logout(
    app: FastAPI, client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")
    login(client, "alice")
    token = client.cookies.get(HOST_COOKIE)
    assert token is not None

    assert client.get("/api/auth/me").status_code == 200

    logout = client.post("/api/auth/logout")

    assert logout.status_code == 200
    assert logout.headers["set-cookie"].startswith(f"{HOST_COOKIE}=")
    assert "Max-Age=0" in logout.headers["set-cookie"]
    with TestClient(app, base_url=API_BASE_URL, cookies={HOST_COOKIE: token}) as replay:
        assert replay.get("/api/auth/me").status_code == 401


def test_cookie_under_default_name_is_ignored(
    app: FastAPI, client: TestClient, user_factory: UserFactory
) -> None:
    user_factory("alice")
    login(client, "alice")
    token = client.cookies.get(HOST_COOKIE)
    assert token is not None

    with TestClient(app, base_url=API_BASE_URL, cookies={"session": token}) as other:
        assert other.get("/api/auth/me").status_code == 401


def test_host_prefix_requires_secure_cookie(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires PATCHPOINT_COOKIE_SECURE=true"):
        Settings(database_path=tmp_path / "test.db", cookie_name=HOST_COOKIE, cookie_secure=False)


@pytest.mark.parametrize(
    "name", ["__Secure-session", "session; Domain=evil.example", "", "1session"]
)
def test_cookie_name_outside_allowed_pattern_is_rejected(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_path=tmp_path / "test.db", cookie_name=name)
