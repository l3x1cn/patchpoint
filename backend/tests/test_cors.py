from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings

FRONTEND_ORIGIN = "http://localhost:5500"
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


def test_simple_request_from_unknown_origin_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": FOREIGN_ORIGIN})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_origin_is_rejected_in_settings(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cors_origins must list explicit origins"):
        Settings(database_path=tmp_path / "test.db", cors_origins=["*"])
