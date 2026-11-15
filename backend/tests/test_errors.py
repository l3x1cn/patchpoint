from collections.abc import Callable
from contextlib import closing

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, execute


def test_database_failure_returns_json_error(
    client: TestClient, settings: Settings, user_factory: Callable[..., int]
) -> None:
    user_factory("alice")
    with closing(connect(settings.database_path)) as conn:
        execute(conn, "DROP TABLE sessions")

    response = client.post("/api/auth/login", json={"username": "alice", "password": "Secret123!"})

    assert response.status_code == 500
    body = response.json()
    assert isinstance(body["error"], str)
    assert body["error"]
