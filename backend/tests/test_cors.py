import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.support import LoginAs, UserFactory

FRONTEND_ORIGIN = "http://patchpoint.localhost:5500"
FOREIGN_ORIGIN = "http://evil.example"


def test_preflight_allows_frontend_origin_with_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/auth/me",
        headers={"Origin": FRONTEND_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_rejects_unknown_origin(client: TestClient) -> None:
    response = client.options(
        "/api/auth/me",
        headers={"Origin": FOREIGN_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preflight_rejects_unlisted_header(client: TestClient) -> None:
    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 400


def test_simple_request_from_unknown_origin_is_rejected(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": FOREIGN_ORIGIN})

    assert response.status_code == 403
    assert response.json() == {"detail": "Origin not allowed"}
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


def test_logout_from_unknown_origin_is_rejected_and_keeps_session(
    user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    session_client = login_as("alice")

    logout = session_client.post("/api/auth/logout", headers={"Origin": FOREIGN_ORIGIN})
    me = session_client.get("/api/auth/me")

    assert logout.status_code == 403
    assert me.status_code == 200


def test_request_from_listed_origin_is_accepted(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": FRONTEND_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_request_without_origin_is_accepted(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200


def test_wildcard_origin_is_rejected_in_settings(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cors_origins must list explicit origins"):
        Settings(database_path=tmp_path / "test.db", cors_origins=["*"])


def test_default_origin_is_not_a_bare_localhost_site(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "test.db")

    hosts = {urlsplit(origin).hostname for origin in settings.cors_origins}

    assert hosts == {"patchpoint.localhost"}


def test_frontend_calls_the_api_on_the_dedicated_hostname() -> None:
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app_js = (frontend / "app.js").read_text(encoding="utf-8")
    index_html = (frontend / "index.html").read_text(encoding="utf-8")

    api_base_url = re.search(r'const API_BASE_URL = "([^"]+)";', app_js)

    assert api_base_url is not None
    assert urlsplit(api_base_url.group(1)).hostname == "patchpoint.localhost"
    assert f"connect-src {api_base_url.group(1)};" in index_html
