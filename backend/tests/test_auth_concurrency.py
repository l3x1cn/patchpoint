import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import anyio
import anyio.to_thread
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient

from app import security
from app.config import Settings
from app.routers import auth as auth_router
from app.security import verify_password
from tests.support import API_BASE_URL, DEFAULT_PASSWORD, UserFactory

HASH_CALLERS = 12
HASH_CALLS = 6
HASH_DURATION_SECONDS = 0.05
WORKER_WAIT_SECONDS = 5.0
CONCURRENT_GUESSES = 20

REGISTER_BODY: dict[str, Any] = {
    "username": "new.user",
    "password": "Register-Pass-2026!",
    "full_name": "New User",
    "department": "HR",
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def async_client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=API_BASE_URL)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("function_name", "path", "body"),
    [
        ("hash_password", "/api/auth/register", REGISTER_BODY),
        (
            "verify_password",
            "/api/auth/login",
            {"username": "alice", "password": "wrong-password"},
        ),
        (
            "simulate_password_check",
            "/api/auth/login",
            {"username": "nobody", "password": "wrong-password"},
        ),
    ],
)
async def test_password_hashing_does_not_block_event_loop(
    app: FastAPI,
    client: TestClient,
    user_factory: UserFactory,
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
    path: str,
    body: dict[str, Any],
) -> None:
    user_factory("alice")
    original: Callable[..., Any] = getattr(auth_router, function_name)
    worker_started = threading.Event()
    health_answered = threading.Event()
    answered_in_time: list[bool] = []

    def blocking(*args: Any) -> Any:
        # Blocks its own thread until the event loop has served another request.
        worker_started.set()
        answered_in_time.append(health_answered.wait(timeout=WORKER_WAIT_SECONDS))
        return original(*args)

    monkeypatch.setattr(auth_router, function_name, blocking)
    results: list[int] = []

    async with async_client(app) as http:

        async def slow_request() -> None:
            results.append((await http.post(path, json=body)).status_code)

        async with anyio.create_task_group() as tasks:
            tasks.start_soon(slow_request)
            await anyio.to_thread.run_sync(worker_started.wait, WORKER_WAIT_SECONDS)
            health = await http.get("/api/health")
            health_answered.set()

    assert health.status_code == 200
    assert answered_in_time == [True]
    assert results[0] in {201, 401}


@pytest.mark.anyio
async def test_concurrent_wrong_guesses_cannot_exceed_lockout(
    app: FastAPI,
    client: TestClient,
    settings: Settings,
    user_factory: UserFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_factory("alice")
    original = verify_password
    verified: list[str] = []

    def counting(password: str, stored_hash: str) -> bool:
        verified.append(password)
        return original(password, stored_hash)

    monkeypatch.setattr(auth_router, "verify_password", counting)
    responses: list[tuple[int, dict[str, Any]]] = []

    async with async_client(app) as http:

        async def guess() -> None:
            response = await http.post(
                "/api/auth/login", json={"username": "alice", "password": "wrong-password"}
            )
            responses.append((response.status_code, response.json()))

        async with anyio.create_task_group() as tasks:
            for _ in range(CONCURRENT_GUESSES):
                tasks.start_soon(guess)

        correct = await http.post(
            "/api/auth/login", json={"username": "alice", "password": DEFAULT_PASSWORD}
        )

    limit = settings.login_max_failures
    statuses = [status for status, _ in responses]
    assert statuses.count(401) == limit
    assert statuses.count(429) == CONCURRENT_GUESSES - limit
    assert len(verified) == limit
    assert {tuple(body.items()) for status, body in responses if status == 401} == {
        (("detail", "Invalid username or password"),)
    }
    assert correct.status_code == 429


class SlowPasswordHasher:
    """Fake Argon2 hasher that records the highest number of simultaneous calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = 0
        self.max_seen = 0

    def _work(self) -> None:
        with self._lock:
            self._running += 1
            self.max_seen = max(self.max_seen, self._running)
        time.sleep(HASH_DURATION_SECONDS)
        with self._lock:
            self._running -= 1

    def hash(self, password: str) -> str:
        self._work()
        return "$argon2id$fake"

    def verify(self, stored_hash: str, password: str) -> bool:
        self._work()
        return True


def test_password_hashing_concurrency_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SlowPasswordHasher()
    monkeypatch.setattr(security, "_password_hasher", fake)

    with ThreadPoolExecutor(max_workers=HASH_CALLERS) as pool:
        futures: list[Future[object]] = [
            pool.submit(security.hash_password, "secret") for _ in range(HASH_CALLS)
        ]
        futures += [
            pool.submit(security.verify_password, "secret", "$argon2id$fake")
            for _ in range(HASH_CALLS)
        ]
        for future in futures:
            future.result()

    assert 2 <= fake.max_seen <= security.PASSWORD_HASH_CONCURRENCY
