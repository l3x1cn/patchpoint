import logging
import sqlite3
from typing import Annotated, Final

from fastapi import APIRouter, HTTPException, Path, Query, Request

from app.audit import log_security_event
from app.database import fetch_all, fetch_one, run, transaction, utc_now_iso
from app.dependencies import AgentUser, CurrentUser, DbConnection
from app.schemas import (
    MAX_SQLITE_INTEGER,
    CommentCreate,
    CommentResponse,
    Role,
    TicketCreate,
    TicketDetailResponse,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
    UserResponse,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

ALLOWED_TRANSITIONS: Final[dict[TicketStatus, frozenset[TicketStatus]]] = {
    TicketStatus.OPEN: frozenset({TicketStatus.IN_PROGRESS, TicketStatus.CLOSED}),
    TicketStatus.IN_PROGRESS: frozenset({TicketStatus.OPEN, TicketStatus.RESOLVED}),
    TicketStatus.RESOLVED: frozenset({TicketStatus.IN_PROGRESS, TicketStatus.CLOSED}),
    TicketStatus.CLOSED: frozenset(),
}

TICKET_SELECT: Final = """
SELECT t.id, t.title, t.description, t.category, t.priority, t.status,
       t.asset_tag, t.location, t.reporter_id, r.full_name AS reporter_name,
       t.assignee_id, a.full_name AS assignee_name, t.created_at, t.updated_at
FROM tickets t
JOIN users r ON r.id = t.reporter_id
LEFT JOIN users a ON a.id = t.assignee_id
"""

COMMENT_SELECT: Final = """
SELECT c.id, c.ticket_id, c.author_id, u.full_name AS author_name, c.body, c.created_at
FROM comments c
JOIN users u ON u.id = c.author_id
"""

LIST_TICKETS_SQL: Final = (
    TICKET_SELECT
    + """
WHERE (:reporter_id IS NULL OR t.reporter_id = :reporter_id)
  AND (:status IS NULL OR t.status = :status)
  AND (:pattern IS NULL
       OR t.title LIKE :pattern ESCAPE '\\'
       OR t.description LIKE :pattern ESCAPE '\\')
ORDER BY t.id DESC
LIMIT :limit OFFSET :offset
"""
)

UPDATE_TICKET_SQL: Final = (
    "UPDATE tickets SET status = COALESCE(:status, status), "
    "priority = COALESCE(:priority, priority), "
    "assignee_id = COALESCE(:assignee_id, assignee_id), "
    "updated_at = :updated_at WHERE id = :ticket_id"
)

PAGE_SIZE_DEFAULT: Final = 50
PAGE_SIZE_MAX: Final = 100
COMMENTS_IN_DETAIL_MAX: Final = 50

type TicketId = Annotated[int, Path(ge=1, le=MAX_SQLITE_INTEGER)]


def escape_like(term: str) -> str:
    """Build a contains-pattern for `LIKE ... ESCAPE '\\'` that matches the term literally."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    return f"%{escaped}%"


def _visible_ticket(
    conn: sqlite3.Connection, ticket_id: int, user: UserResponse, request: Request
) -> sqlite3.Row:
    """Return the ticket or raise 404, identically for missing and foreign tickets."""
    row = fetch_one(conn, f"{TICKET_SELECT} WHERE t.id = ?", (ticket_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if user.role == Role.EMPLOYEE and row["reporter_id"] != user.id:
        log_security_event(
            "access_denied",
            request,
            level=logging.WARNING,
            user_id=user.id,
            reason="not_ticket_owner",
            path=request.url.path,
            ticket_id=ticket_id,
        )
        raise HTTPException(status_code=404, detail="Ticket not found")

    return row


@router.post("", status_code=201)
async def create_ticket(
    payload: TicketCreate, user: CurrentUser, conn: DbConnection, request: Request
) -> TicketResponse:
    now = utc_now_iso()
    with transaction(conn):
        ticket_id = run(
            conn,
            "INSERT INTO tickets (title, description, category, priority, status, asset_tag, "
            "location, reporter_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)",
            (
                payload.title,
                payload.description,
                payload.category.value,
                payload.priority.value,
                payload.asset_tag,
                payload.location,
                user.id,
                now,
                now,
            ),
        )

    row = _visible_ticket(conn, ticket_id, user, request)

    return TicketResponse.model_validate(dict(row))


@router.get("")
async def list_tickets(
    user: CurrentUser,
    conn: DbConnection,
    status: TicketStatus | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0, le=MAX_SQLITE_INTEGER)] = 0,
) -> list[TicketResponse]:
    rows = fetch_all(
        conn,
        LIST_TICKETS_SQL,
        {
            "reporter_id": user.id if user.role == Role.EMPLOYEE else None,
            "status": status.value if status else None,
            "pattern": escape_like(search) if search else None,
            "limit": limit,
            "offset": offset,
        },
    )

    return [TicketResponse.model_validate(dict(row)) for row in rows]


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: TicketId, user: CurrentUser, conn: DbConnection, request: Request
) -> TicketDetailResponse:
    row = _visible_ticket(conn, ticket_id, user, request)
    comment_rows = fetch_all(
        conn,
        f"{COMMENT_SELECT} WHERE c.ticket_id = ? ORDER BY c.id DESC LIMIT ?",
        (ticket_id, COMMENTS_IN_DETAIL_MAX),
    )
    count_row = fetch_one(conn, "SELECT COUNT(*) FROM comments WHERE ticket_id = ?", (ticket_id,))
    comment_count = count_row[0] if count_row is not None else 0
    # Newest N, shown oldest-first like the full thread.
    comments = [CommentResponse.model_validate(dict(c)) for c in reversed(comment_rows)]

    return TicketDetailResponse.model_validate(
        {**dict(row), "comments": comments, "comment_count": comment_count}
    )


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: TicketId,
    payload: TicketUpdate,
    agent: AgentUser,
    conn: DbConnection,
    request: Request,
) -> TicketResponse:
    if payload.status is None and payload.priority is None and payload.assignee_id is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    current = _visible_ticket(conn, ticket_id, agent, request)
    current_status = TicketStatus(current["status"])
    if (
        payload.status is not None
        and payload.status != current_status
        and payload.status not in ALLOWED_TRANSITIONS[current_status]
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition: {current_status} -> {payload.status}",
        )

    if payload.assignee_id is not None:
        assignee = fetch_one(conn, "SELECT role FROM users WHERE id = ?", (payload.assignee_id,))
        if assignee is None or assignee["role"] != Role.AGENT:
            raise HTTPException(status_code=400, detail="Assignee must be a helpdesk agent")

    status = payload.status.value if payload.status else None
    priority = payload.priority.value if payload.priority else None
    with transaction(conn):
        run(
            conn,
            UPDATE_TICKET_SQL,
            {
                "status": status,
                "priority": priority,
                "assignee_id": payload.assignee_id,
                "updated_at": utc_now_iso(),
                "ticket_id": ticket_id,
            },
        )

    log_security_event(
        "ticket_updated",
        request,
        user_id=agent.id,
        ticket_id=ticket_id,
        status=status,
        priority=priority,
        assignee_id=payload.assignee_id,
    )
    row = _visible_ticket(conn, ticket_id, agent, request)

    return TicketResponse.model_validate(dict(row))


@router.post("/{ticket_id}/comments", status_code=201)
async def add_comment(
    ticket_id: TicketId,
    payload: CommentCreate,
    user: CurrentUser,
    conn: DbConnection,
    request: Request,
) -> CommentResponse:
    _visible_ticket(conn, ticket_id, user, request)

    now = utc_now_iso()
    with transaction(conn):
        comment_id = run(
            conn,
            "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, user.id, payload.body, now),
        )
        run(conn, "UPDATE tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))

    row = fetch_one(conn, f"{COMMENT_SELECT} WHERE c.id = ?", (comment_id,))
    if row is None:
        raise HTTPException(status_code=500, detail="Comment was not created")

    return CommentResponse.model_validate(dict(row))
