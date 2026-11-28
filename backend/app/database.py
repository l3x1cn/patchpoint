import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, NamedTuple

from app.audit import log_security_event
from app.schemas import Role, TicketCategory, TicketPriority, TicketStatus, UserResponse
from app.security import hash_password, password_policy_violation

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION: Final = 2
SQLITE_BUSY_TIMEOUT_SECONDS: Final = 5.0
USER_COLUMNS: Final = ("id", "username", "full_name", "department", "role", "created_at")

type SqlParams = Sequence[object] | Mapping[str, object]


class DemoUser(NamedTuple):
    username: str
    full_name: str
    department: str
    role: Role


class DemoTicket(NamedTuple):
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    asset_tag: str
    location: str
    reporter: str
    assignee: str | None


class DemoComment(NamedTuple):
    ticket_title: str
    author: str
    body: str


DEMO_USERS: Final = (
    DemoUser("helpdesk", "Piotr Serwisant", "IT Helpdesk", Role.AGENT),
    DemoUser("jan.kowalski", "Jan Kowalski", "Księgowość", Role.EMPLOYEE),
    DemoUser("anna.nowak", "Anna Nowak", "Marketing", Role.EMPLOYEE),
)

DEMO_TICKETS: Final = (
    DemoTicket(
        title="Laptop nie uruchamia się po aktualizacji",
        description="Po nocnej aktualizacji systemu laptop zatrzymuje się na logo producenta.",
        category=TicketCategory.LAPTOP,
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        asset_tag="LAP-0042",
        location="B-204",
        reporter="jan.kowalski",
        assignee=None,
    ),
    DemoTicket(
        title="Drukarka zacina papier",
        description="Drukarka sieciowa na 2. piętrze zacina papier przy druku dwustronnym.",
        category=TicketCategory.PRINTER,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.IN_PROGRESS,
        asset_tag="PRN-0007",
        location="Korytarz, 2. piętro",
        reporter="jan.kowalski",
        assignee="helpdesk",
    ),
    DemoTicket(
        title="Migający monitor",
        description="Monitor zewnętrzny miga co kilka sekund po podłączeniu przez HDMI.",
        category=TicketCategory.MONITOR,
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        asset_tag="MON-0113",
        location="C-012",
        reporter="anna.nowak",
        assignee=None,
    ),
)

DEMO_COMMENTS: Final = (
    DemoComment(
        ticket_title="Drukarka zacina papier",
        author="helpdesk",
        body="Zamówiono nowy podajnik papieru, wymiana planowana na piątek.",
    ),
)


class DatabaseError(Exception):
    def __init__(self, sql: str, original: sqlite3.Error) -> None:
        super().__init__(str(original))
        self.sql = sql
        self.original = original


class SchemaVersionError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def isoformat(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def utc_now_iso() -> str:
    return isoformat(utc_now())


def connect(database_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        database_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fetch_one(conn: sqlite3.Connection, sql: str, params: SqlParams = ()) -> sqlite3.Row | None:
    try:
        row: sqlite3.Row | None = conn.execute(sql, params).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, exc) from exc
    return row


def fetch_all(conn: sqlite3.Connection, sql: str, params: SqlParams = ()) -> list[sqlite3.Row]:
    try:
        rows: list[sqlite3.Row] = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseError(sql, exc) from exc
    return rows


def run(conn: sqlite3.Connection, sql: str, params: SqlParams = ()) -> int:
    """Execute a write statement without committing; call inside `transaction`."""
    try:
        cursor = conn.execute(sql, params)
    except sqlite3.Error as exc:
        raise DatabaseError(sql, exc) from exc
    return cursor.lastrowid or 0


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """Commit the writes of the block; roll back if the block or the commit fails."""
    committed = False
    try:
        yield

        try:
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("COMMIT", exc) from exc
        committed = True
    finally:
        if not committed:
            conn.rollback()


def user_from_row(row: sqlite3.Row) -> UserResponse:
    return UserResponse.model_validate({column: row[column] for column in USER_COLUMNS})


def create_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    full_name: str,
    department: str,
    role: Role,
) -> int:
    return run(
        conn,
        "INSERT INTO users (username, password_hash, full_name, department, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, full_name, department, role.value, utc_now_iso()),
    )


def _user_id(conn: sqlite3.Connection, username: str) -> int:
    row = fetch_one(conn, "SELECT id FROM users WHERE username = ?", (username,))
    if row is None:
        raise ValueError(f"Unknown demo user: {username}")

    user_id: int = row["id"]
    return user_id


def seed_demo_data(conn: sqlite3.Connection, *, password: str) -> None:
    for user in DEMO_USERS:
        violation = password_policy_violation(password, user.username)
        if violation is not None:
            raise ValueError(
                f"PATCHPOINT_DEMO_PASSWORD rejected for demo user {user.username}: {violation}"
            )

    row = fetch_one(conn, "SELECT COUNT(*) AS n FROM users")
    if row is None or row["n"] != 0:
        return

    with transaction(conn):
        for user in DEMO_USERS:
            create_user(
                conn,
                username=user.username,
                password_hash=hash_password(password),
                full_name=user.full_name,
                department=user.department,
                role=user.role,
            )

        ticket_ids: dict[str, int] = {}
        for ticket in DEMO_TICKETS:
            now = utc_now_iso()
            assignee_id = _user_id(conn, ticket.assignee) if ticket.assignee else None
            ticket_ids[ticket.title] = run(
                conn,
                "INSERT INTO tickets (title, description, category, priority, status, asset_tag, "
                "location, reporter_id, assignee_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket.title,
                    ticket.description,
                    ticket.category.value,
                    ticket.priority.value,
                    ticket.status.value,
                    ticket.asset_tag,
                    ticket.location,
                    _user_id(conn, ticket.reporter),
                    assignee_id,
                    now,
                    now,
                ),
            )

        for comment in DEMO_COMMENTS:
            run(
                conn,
                "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
                (
                    ticket_ids[comment.ticket_title],
                    _user_id(conn, comment.author),
                    comment.body,
                    utc_now_iso(),
                ),
            )

    log_security_event("demo_data_seeded", None, users=len(DEMO_USERS))


def _check_schema_version(conn: sqlite3.Connection, database_path: Path) -> None:
    users_table = fetch_one(
        conn, "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    )
    if users_table is None:
        return

    version_row = fetch_one(conn, "PRAGMA user_version")
    version: int = version_row[0] if version_row is not None else 0
    if version != SCHEMA_VERSION:
        raise SchemaVersionError(
            f"Database {database_path} uses schema version {version}, "
            f"expected {SCHEMA_VERSION}. Delete the file and restart the API to recreate it."
        )


def init_db(database_path: Path, *, demo_password: str | None) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect(database_path)) as conn:
        _check_schema_version(conn, database_path)
        # SQLite runs on the event-loop thread, so a commit blocked by another connection would
        # stall every request. In WAL mode readers outside the API (backups, the sqlite3 shell,
        # QA checks) do not block its writes. The mode is stored in the database file.
        fetch_one(conn, "PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if demo_password is not None:
            seed_demo_data(conn, password=demo_password)
