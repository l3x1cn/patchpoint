from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, create_user, transaction
from app.main import create_app
from app.schemas import Role
from tests.support import (
    API_BASE_URL,
    DEFAULT_PASSWORD,
    DEMO_PASSWORD,
    LoginAs,
    TicketFactory,
    UserFactory,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "test.db")


@pytest.fixture
def seeded_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "seeded.db", seed_demo_data=True, demo_password=DEMO_PASSWORD
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # The session cookie is Secure, so the client must talk to an https origin.
    with TestClient(app, base_url=API_BASE_URL) as test_client:
        yield test_client


@pytest.fixture
def user_factory(client: TestClient, settings: Settings) -> UserFactory:
    def create(
        username: str,
        *,
        role: Role = Role.EMPLOYEE,
        password: str = DEFAULT_PASSWORD,
        full_name: str | None = None,
    ) -> int:
        with closing(connect(settings.database_path)) as conn, transaction(conn):
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
def login_as(app: FastAPI, client: TestClient) -> Iterator[LoginAs]:
    clients: list[TestClient] = []

    def login(username: str, password: str = DEFAULT_PASSWORD) -> TestClient:
        session_client = TestClient(app, base_url=API_BASE_URL)
        clients.append(session_client)
        response = session_client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200
        return session_client

    yield login

    for session_client in clients:
        session_client.close()


@pytest.fixture
def ticket_factory() -> TicketFactory:
    def create(
        client: TestClient,
        *,
        title: str = "Laptop się przegrzewa",
        description: str = "Wentylator pracuje głośno, obudowa jest gorąca.",
        category: str = "laptop",
        priority: str = "high",
    ) -> int:
        response = client.post(
            "/api/tickets",
            json={
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
            },
        )
        assert response.status_code == 201
        ticket_id: int = response.json()["id"]
        return ticket_id

    return create
