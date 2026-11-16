import hashlib
import json
import re
from collections.abc import Sequence
from contextlib import closing
from datetime import datetime, timedelta
from typing import Final

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, fetch_all, fetch_one, isoformat, run, transaction, utc_now
from tests.support import API_BASE_URL, LoginAs, UserFactory

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43,}")
SESSION_UPDATES: Final = {
    "last_seen_at": "UPDATE sessions SET last_seen_at = ?",
    "expires_at": "UPDATE sessions SET expires_at = ?",
}


def session_token(client: TestClient) -> str:
    token = client.cookies.get("session")
    assert token
    return token


def update_session(settings: Settings, column: str, moment: datetime) -> None:
    with closing(connect(settings.database_path)) as conn, transaction(conn):
        run(conn, SESSION_UPDATES[column], (isoformat(moment),))


def count_sessions(settings: Settings) -> int:
    with closing(connect(settings.database_path)) as conn:
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM sessions")
    assert row is not None
    count: int = row["n"]
    return count


def test_logout_invalidates_session_on_server(
    app: FastAPI, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    session_client = login_as("alice")
    token = session_token(session_client)

    session_client.post("/api/auth/logout")

    with TestClient(app, base_url=API_BASE_URL, cookies={"session": token}) as replay:
        response = replay.get("/api/auth/me")
    assert response.status_code == 401


def test_session_tokens_are_random_and_stored_hashed(
    settings: Settings, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    first = session_token(login_as("alice"))
    second = session_token(login_as("alice"))

    assert first != second
    assert TOKEN_PATTERN.fullmatch(first)
    assert TOKEN_PATTERN.fullmatch(second)
    with closing(connect(settings.database_path)) as conn:
        rows = fetch_all(conn, "SELECT * FROM sessions")
    stored_hashes = {row["token_hash"] for row in rows}
    assert stored_hashes == {
        hashlib.sha256(first.encode("utf-8")).hexdigest(),
        hashlib.sha256(second.encode("utf-8")).hexdigest(),
    }
    for row in rows:
        assert first not in tuple(row)
        assert second not in tuple(row)


def test_idle_session_expires(
    settings: Settings, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    session_client = login_as("alice")
    update_session(settings, "last_seen_at", utc_now() - timedelta(minutes=31))

    response = session_client.get("/api/auth/me")

    assert response.status_code == 401
    assert count_sessions(settings) == 0


def test_session_expires_after_absolute_lifetime(
    settings: Settings, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    session_client = login_as("alice")
    update_session(settings, "expires_at", utc_now() - timedelta(seconds=1))

    response = session_client.get("/api/auth/me")

    assert response.status_code == 401
    assert count_sessions(settings) == 0


def test_activity_extends_idle_window(
    settings: Settings, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    session_client = login_as("alice")
    update_session(settings, "last_seen_at", utc_now() - timedelta(minutes=20))

    response = session_client.get("/api/auth/me")

    assert response.status_code == 200
    with closing(connect(settings.database_path)) as conn:
        row = fetch_one(conn, "SELECT last_seen_at FROM sessions")
    assert row is not None
    assert datetime.fromisoformat(row["last_seen_at"]) >= utc_now() - timedelta(minutes=1)


@pytest.mark.parametrize(
    ("column", "age", "reason"),
    [
        ("last_seen_at", timedelta(minutes=31), "idle_timeout"),
        ("expires_at", timedelta(seconds=1), "absolute_timeout"),
    ],
)
def test_rejected_sessions_are_logged(
    settings: Settings,
    user_factory: UserFactory,
    login_as: LoginAs,
    caplog: pytest.LogCaptureFixture,
    column: str,
    age: timedelta,
    reason: str,
) -> None:
    user_id = user_factory("alice")
    session_client = login_as("alice")
    update_session(settings, column, utc_now() - age)

    session_client.get("/api/auth/me")

    events: Sequence[dict[str, object]] = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "patchpoint.security"
    ]
    rejected = [event for event in events if event["event"] == "session_rejected"]
    assert len(rejected) == 1
    assert rejected[0]["reason"] == reason
    assert rejected[0]["user_id"] == user_id


def test_expired_sessions_are_purged_on_login(
    settings: Settings, user_factory: UserFactory, login_as: LoginAs
) -> None:
    user_factory("alice")
    login_as("alice")
    update_session(settings, "expires_at", utc_now() - timedelta(seconds=1))

    login_as("alice")

    assert count_sessions(settings) == 1
