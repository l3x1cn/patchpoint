import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.schemas import Role
from app.security import hash_password

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEMO_USERS: Final = (
    ("admin", "admin123", "Administrator Systemu", "IT", Role.AGENT),
    ("helpdesk", "helpdesk123", "Piotr Serwisant", "IT Helpdesk", Role.AGENT),
    ("jan.kowalski", "password123", "Jan Kowalski", "Księgowość", Role.EMPLOYEE),
    ("anna.nowak", "password123", "Anna Nowak", "Marketing", Role.EMPLOYEE),
)


class DatabaseError(Exception):
    def __init__(self, sql: str, params: Sequence[object], original: sqlite3.Error) -> None:
        super().__init__(str(original))
        self.sql = sql
        self.params = params
        self.original = original


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(database_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fetch_one(
    conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()
) -> sqlite3.Row | None:
    try:
        row: sqlite3.Row | None = conn.execute(sql, params).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, params, exc) from exc
    return row


def fetch_all(
    conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()
) -> list[sqlite3.Row]:
    try:
        rows: list[sqlite3.Row] = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, params, exc) from exc
    return rows


def execute(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> int:
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, params, exc) from exc
    return cursor.lastrowid or 0


def create_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    full_name: str,
    department: str,
    role: Role,
) -> int:
    return execute(
        conn,
        "INSERT INTO users (username, password_hash, full_name, department, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, hash_password(password), full_name, department, role.value, utc_now_iso()),
    )


def seed_demo_data(conn: sqlite3.Connection) -> None:
    row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users")
    if row is None or row["n"] != 0:
        return

    for username, password, full_name, department, role in DEMO_USERS:
        create_user(
            conn,
            username=username,
            password=password,
            full_name=full_name,
            department=department,
            role=role,
        )


def init_db(database_path: Path, *, with_demo_data: bool) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect(database_path)) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if with_demo_data:
            seed_demo_data(conn)
        conn.commit()
