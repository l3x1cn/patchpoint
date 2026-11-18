import json
import logging
import re
import sqlite3
from contextlib import closing

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from tests.support import DEFAULT_PASSWORD, ERRORS_LOGGER, UserFactory, log_records

ERROR_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def test_database_error_returns_generic_body_and_logs_details(
    client: TestClient,
    settings: Settings,
    user_factory: UserFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_factory("alice")
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.execute("DROP TABLE sessions")
        conn.commit()

    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 500
    body = response.json()
    assert set(body) == {"detail", "error_id"}
    assert body["detail"] == "Internal server error"
    assert ERROR_ID_PATTERN.fullmatch(body["error_id"])
    for leaked in ("sessions", "INSERT", "sqlite", "Traceback", str(settings.database_path)):
        assert leaked not in response.text

    records = log_records(caplog, ERRORS_LOGGER)
    assert len(records) == 1
    entry = json.loads(records[0].getMessage())
    assert entry["event"] == "internal_error"
    assert entry["error_id"] == body["error_id"]
    assert "sessions" in entry["sql"]
    assert records[0].exc_info is not None


def test_unhandled_exception_returns_generic_json(app: FastAPI) -> None:
    @app.get("/api/test-failure")
    async def failure() -> None:
        raise RuntimeError("failure-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/test-failure")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    assert ERROR_ID_PATTERN.fullmatch(body["error_id"])
    assert "failure-detail" not in response.text
    assert "Traceback" not in response.text


def test_unhandled_exception_is_logged_without_leaking_to_client(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/api/test-failure")
    async def failure() -> None:
        raise RuntimeError("failure-detail")

    with (
        caplog.at_level(logging.ERROR, logger=ERRORS_LOGGER),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/api/test-failure")

    records = log_records(caplog, ERRORS_LOGGER)
    assert len(records) == 1
    entry = json.loads(records[0].getMessage())
    assert entry["error_id"] == response.json()["error_id"]
    assert entry["exception"] == "RuntimeError"
    assert entry["sql"] is None
    assert entry["path"] == "/api/test-failure"
