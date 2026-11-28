import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.database import (
    SCHEMA_VERSION,
    DatabaseError,
    SchemaVersionError,
    connect,
    fetch_one,
    run,
    transaction,
)
from app.main import create_app
from app.security import hash_password, password_policy_violation, verify_password
from tests.support import DEFAULT_PASSWORD, UserFactory


def count_all_users(database_path: Path) -> int:
    with closing(connect(database_path)) as conn:
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users")
    assert row is not None
    count: int = row["n"]
    return count


def test_password_hashes_use_argon2id() -> None:
    password_hash = hash_password(DEFAULT_PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert verify_password(DEFAULT_PASSWORD, password_hash)
    assert not verify_password("another-password-value", password_hash)


def test_legacy_md5_hash_is_rejected() -> None:
    assert not verify_password("password123", "482c811da5d5b4bc6d497ffa98491e38")


@pytest.mark.parametrize(
    ("password", "username", "violation"),
    [
        ("x" * 14, "alice", "Password must be at least 15 characters long"),
        ("x" * 129, "alice", "Password must be at most 128 characters long"),
        ("My-ALICE-password-1", "alice", "Password must not contain the username"),
        ("x" * 15, "alice", None),
        ("x" * 128, "alice", None),
    ],
)
def test_password_policy(password: str, username: str, violation: str | None) -> None:
    assert password_policy_violation(password, username) == violation


def test_fresh_database_has_current_schema_version(client: TestClient, settings: Settings) -> None:
    with closing(connect(settings.database_path)) as conn:
        row = fetch_one(conn, "PRAGMA user_version")

    assert row is not None
    assert row[0] == SCHEMA_VERSION


def test_outdated_schema_blocks_startup(tmp_path: Path) -> None:
    database_path = tmp_path / "old.db"
    with closing(sqlite3.connect(database_path)) as conn:
        conn.execute("CREATE TABLE users (id INTEGER)")
        conn.commit()
    app = create_app(Settings(database_path=database_path))

    with pytest.raises(SchemaVersionError, match="schema version 0"), TestClient(app):
        pass


def test_demo_seed_requires_password(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="PATCHPOINT_DEMO_PASSWORD is required"):
        Settings(database_path=tmp_path / "demo.db", seed_demo_data=True)


def test_demo_seed_rejects_weak_password(tmp_path: Path) -> None:
    database_path = tmp_path / "weak.db"
    app = create_app(
        Settings(database_path=database_path, seed_demo_data=True, demo_password="short-pass")
    )

    with pytest.raises(ValueError, match="PATCHPOINT_DEMO_PASSWORD rejected"), TestClient(app):
        pass

    assert count_all_users(database_path) == 0


def test_transaction_rolls_back_on_error(client: TestClient, settings: Settings) -> None:
    with (
        closing(connect(settings.database_path)) as conn,
        pytest.raises(RuntimeError, match="boom"),
        transaction(conn),
    ):
        run(
            conn,
            "INSERT INTO users (username, password_hash, full_name, created_at) "
            "VALUES ('ghost', 'x', 'Ghost', '2026-01-01T00:00:00+00:00')",
        )
        raise RuntimeError("boom")

    assert count_all_users(settings.database_path) == 0


def test_transaction_rolls_back_after_failed_commit(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "deferred.db")) as conn:
        conn.executescript(
            "CREATE TABLE parent (id INTEGER PRIMARY KEY);"
            "CREATE TABLE child (parent_id INTEGER "
            "REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED);"
        )

        with pytest.raises(DatabaseError) as excinfo, transaction(conn):
            run(conn, "INSERT INTO child (parent_id) VALUES (999)")

        assert excinfo.value.sql == "COMMIT"
        assert not conn.in_transaction
        row = fetch_one(conn, "SELECT COUNT(*) AS n FROM child")

    assert row is not None
    assert row["n"] == 0


def test_database_uses_wal_journal_mode(client: TestClient, settings: Settings) -> None:
    with closing(connect(settings.database_path)) as conn:
        row = fetch_one(conn, "PRAGMA journal_mode")

    assert row is not None
    assert row[0] == "wal"


def test_login_is_not_blocked_by_an_external_read_transaction(
    client: TestClient, settings: Settings, user_factory: UserFactory
) -> None:
    user_factory("alice")
    reader = sqlite3.connect(settings.database_path, isolation_level=None)

    try:
        reader.execute("BEGIN")
        reader.execute("SELECT COUNT(*) FROM users").fetchone()

        response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong-password"}
        )
    finally:
        reader.execute("ROLLBACK")
        reader.close()

    assert response.status_code == 401
