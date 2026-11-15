from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, create_user
from app.main import create_app
from app.schemas import Role

DEFAULT_PASSWORD = "Secret123!"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "test.db", seed_demo_data=False)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_factory(client: TestClient, settings: Settings) -> Callable[..., int]:
    def create(
        username: str,
        *,
        role: Role = Role.EMPLOYEE,
        password: str = DEFAULT_PASSWORD,
        full_name: str | None = None,
    ) -> int:
        with closing(connect(settings.database_path)) as conn:
            return create_user(
                conn,
                username=username,
                password=password,
                full_name=full_name or username,
                department="QA",
                role=role,
            )

    return create


@pytest.fixture
def login_as(app: FastAPI, client: TestClient) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def login(username: str, password: str = DEFAULT_PASSWORD) -> TestClient:
        session_client = TestClient(app)
        clients.append(session_client)
        response = session_client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200
        return session_client

    yield login

    for session_client in clients:
        session_client.close()
