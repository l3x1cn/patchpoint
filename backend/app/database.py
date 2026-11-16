import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.schemas import Role, TicketCategory, TicketPriority, TicketStatus
from app.security import hash_password

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEMO_USERS: Final = (
    ("admin", "admin123", "Administrator Systemu", "IT", Role.AGENT),
    ("helpdesk", "helpdesk123", "Piotr Serwisant", "IT Helpdesk", Role.AGENT),
    ("jan.kowalski", "password123", "Jan Kowalski", "Księgowość", Role.EMPLOYEE),
    ("anna.nowak", "password123", "Anna Nowak", "Marketing", Role.EMPLOYEE),
)


class DatabaseError(Exception):
    def __init__(self, sql: str, original: sqlite3.Error) -> None:
        super().__init__(str(original))
        self.sql = sql
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
        raise DatabaseError(sql, exc) from exc
    return row


def fetch_all(
    conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()
) -> list[sqlite3.Row]:
    try:
        rows: list[sqlite3.Row] = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, exc) from exc
    return rows


def execute(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> int:
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, exc) from exc
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


def insert_demo_ticket(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str,
    category: TicketCategory,
    priority: TicketPriority,
    status: TicketStatus,
    asset_tag: str,
    location: str,
    reporter_username: str,
    assignee_username: str | None,
) -> int:
    reporter = fetch_one(conn, "SELECT id FROM users WHERE username = ?", (reporter_username,))
    assignee = (
        fetch_one(conn, "SELECT id FROM users WHERE username = ?", (assignee_username,))
        if assignee_username
        else None
    )
    if reporter is None:
        raise ValueError(f"Unknown demo user: {reporter_username}")

    now = utc_now_iso()
    return execute(
        conn,
        "INSERT INTO tickets (title, description, category, priority, status, asset_tag, "
        "location, reporter_id, assignee_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            title,
            description,
            category.value,
            priority.value,
            status.value,
            asset_tag,
            location,
            reporter["id"],
            assignee["id"] if assignee else None,
            now,
            now,
        ),
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

    insert_demo_ticket(
        conn,
        title="Laptop nie uruchamia się po aktualizacji",
        description="Po nocnej aktualizacji systemu laptop zatrzymuje się na logo producenta.",
        category=TicketCategory.LAPTOP,
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        asset_tag="LAP-0042",
        location="B-204",
        reporter_username="jan.kowalski",
        assignee_username=None,
    )
    printer_ticket_id = insert_demo_ticket(
        conn,
        title="Drukarka zacina papier",
        description="Drukarka sieciowa na 2. piętrze zacina papier przy druku dwustronnym.",
        category=TicketCategory.PRINTER,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.IN_PROGRESS,
        asset_tag="PRN-0007",
        location="Korytarz, 2. piętro",
        reporter_username="jan.kowalski",
        assignee_username="helpdesk",
    )
    insert_demo_ticket(
        conn,
        title="Migający monitor",
        description="Monitor zewnętrzny miga co kilka sekund po podłączeniu przez HDMI.",
        category=TicketCategory.MONITOR,
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        asset_tag="MON-0113",
        location="C-012",
        reporter_username="anna.nowak",
        assignee_username=None,
    )

    helpdesk = fetch_one(conn, "SELECT id FROM users WHERE username = ?", ("helpdesk",))
    if helpdesk is None:
        raise ValueError("Unknown demo user: helpdesk")
    execute(
        conn,
        "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
        (
            printer_ticket_id,
            helpdesk["id"],
            "Zamówiono nowy podajnik papieru, wymiana planowana na piątek.",
            utc_now_iso(),
        ),
    )


def init_db(database_path: Path, *, with_demo_data: bool) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect(database_path)) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if with_demo_data:
            seed_demo_data(conn)
        conn.commit()
