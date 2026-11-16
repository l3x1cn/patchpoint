from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.middleware import API_SECURITY_HEADERS, COMMON_SECURITY_HEADERS

DOC_PATHS = ("/docs", "/redoc", "/openapi.json")
OVERSIZED_BODY_BYTES = 70_000


@pytest.fixture
def docs_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(database_path=tmp_path / "docs.db", seed_demo_data=False, docs_enabled=True)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.mark.parametrize("path", DOC_PATHS)
def test_api_docs_are_disabled_by_default(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", DOC_PATHS)
def test_api_docs_can_be_enabled_for_development(docs_client: TestClient, path: str) -> None:
    assert docs_client.get(path).status_code == 200


def test_api_responses_carry_security_headers(client: TestClient) -> None:
    response = client.get("/api/health")

    for name, value in {**COMMON_SECURITY_HEADERS, **API_SECURITY_HEADERS}.items():
        assert response.headers[name] == value


def test_non_api_responses_skip_api_only_headers(docs_client: TestClient) -> None:
    response = docs_client.get("/docs")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" not in response.headers


def test_oversized_request_body_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        content=b"x" * OVERSIZED_BODY_BYTES,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
