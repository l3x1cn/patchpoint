import sqlite3
from datetime import datetime, timedelta

from app.config import Settings
from app.database import (
    fetch_one,
    isoformat,
    run,
    transaction,
    user_from_row,
    utc_now,
)
from app.schemas import UserResponse
from app.security import generate_session_token, hash_session_token


class SessionRejectedError(Exception):
    """Raised for an unknown, idle-expired or absolutely expired session token."""

    def __init__(self, reason: str, user_id: int | None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.user_id = user_id


def create_session(conn: sqlite3.Connection, *, user_id: int, settings: Settings) -> str:
    token = generate_session_token()
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.session_absolute_minutes)

    with transaction(conn):
        run(conn, "DELETE FROM sessions WHERE expires_at <= ?", (isoformat(now),))
        run(
            conn,
            "INSERT INTO sessions (token_hash, user_id, created_at, last_seen_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                hash_session_token(token),
                user_id,
                isoformat(now),
                isoformat(now),
                isoformat(expires_at),
            ),
        )

    return token


def _delete_session(conn: sqlite3.Connection, token_hash: str) -> None:
    with transaction(conn):
        run(conn, "DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def authenticate_session(conn: sqlite3.Connection, token: str, settings: Settings) -> UserResponse:
    """Return the session owner and refresh the idle window, or raise `SessionRejectedError`."""
    token_hash = hash_session_token(token)
    row = fetch_one(
        conn,
        "SELECT u.id, u.username, u.full_name, u.department, u.role, u.created_at, "
        "s.last_seen_at, s.expires_at "
        "FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
        (token_hash,),
    )
    if row is None:
        raise SessionRejectedError("unknown", None)

    now = utc_now()
    user_id: int = row["id"]
    if now >= datetime.fromisoformat(row["expires_at"]):
        _delete_session(conn, token_hash)
        raise SessionRejectedError("absolute_timeout", user_id)

    idle_limit = timedelta(minutes=settings.session_idle_minutes)
    if now - datetime.fromisoformat(row["last_seen_at"]) >= idle_limit:
        _delete_session(conn, token_hash)
        raise SessionRejectedError("idle_timeout", user_id)

    with transaction(conn):
        run(
            conn,
            "UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?",
            (isoformat(now), token_hash),
        )

    return user_from_row(row)


def end_session(conn: sqlite3.Connection, token: str) -> int | None:
    """Delete the session on the server and return its owner, if the session existed."""
    token_hash = hash_session_token(token)
    row = fetch_one(conn, "SELECT user_id FROM sessions WHERE token_hash = ?", (token_hash,))
    _delete_session(conn, token_hash)
    if row is None:
        return None

    user_id: int = row["user_id"]
    return user_id


def _lockout_window_start(settings: Settings) -> str:
    return isoformat(utc_now() - timedelta(minutes=settings.login_lockout_minutes))


def is_login_blocked(conn: sqlite3.Connection, username: str, settings: Settings) -> bool:
    row = fetch_one(
        conn,
        "SELECT COUNT(*) AS n FROM login_failures WHERE username = ? AND attempted_at > ?",
        (username, _lockout_window_start(settings)),
    )

    return row is not None and row["n"] >= settings.login_max_failures


def record_login_failure(conn: sqlite3.Connection, username: str, settings: Settings) -> None:
    with transaction(conn):
        run(
            conn,
            "DELETE FROM login_failures WHERE attempted_at <= ?",
            (_lockout_window_start(settings),),
        )
        run(
            conn,
            "INSERT INTO login_failures (username, attempted_at) VALUES (?, ?)",
            (username, isoformat(utc_now())),
        )


def clear_login_failures(conn: sqlite3.Connection, username: str) -> None:
    with transaction(conn):
        run(conn, "DELETE FROM login_failures WHERE username = ?", (username,))
