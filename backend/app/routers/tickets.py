from typing import Final

from fastapi import APIRouter, Depends, HTTPException

from app.database import fetch_all, fetch_one, run, transaction, utc_now_iso
from app.dependencies import CurrentUser, DbConnection, get_current_user, require_agent
from app.schemas import (
    CommentCreate,
    CommentResponse,
    Role,
    TicketCreate,
    TicketDetailResponse,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
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


@router.post("", status_code=201)
async def create_ticket(
    payload: TicketCreate, user: CurrentUser, conn: DbConnection
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

    row = fetch_one(conn, f"{TICKET_SELECT} WHERE t.id = ?", (ticket_id,))
    if row is None:
        raise HTTPException(status_code=500, detail="Ticket was not created")

    return TicketResponse.model_validate(dict(row))


@router.get("")
async def list_tickets(
    user: CurrentUser,
    conn: DbConnection,
    status: TicketStatus | None = None,
    search: str | None = None,
) -> list[TicketResponse]:
    conditions: list[str] = []
    if user.role == Role.EMPLOYEE:
        conditions.append(f"t.reporter_id = {user.id}")
    if status:
        conditions.append(f"t.status = '{status}'")
    if search:
        conditions.append(f"(t.title LIKE '%{search}%' OR t.description LIKE '%{search}%')")

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = fetch_all(conn, f"{TICKET_SELECT}{where} ORDER BY t.id DESC")

    return [TicketResponse.model_validate(dict(row)) for row in rows]


@router.get("/{ticket_id}", dependencies=[Depends(get_current_user)])
async def get_ticket(ticket_id: int, conn: DbConnection) -> TicketDetailResponse:
    row = fetch_one(conn, f"{TICKET_SELECT} WHERE t.id = ?", (ticket_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment_rows = fetch_all(
        conn, f"{COMMENT_SELECT} WHERE c.ticket_id = ? ORDER BY c.id", (ticket_id,)
    )
    comments = [CommentResponse.model_validate(dict(c)) for c in comment_rows]

    return TicketDetailResponse.model_validate({**dict(row), "comments": comments})


@router.patch("/{ticket_id}", dependencies=[Depends(require_agent)])
async def update_ticket(
    ticket_id: int, payload: TicketUpdate, conn: DbConnection
) -> TicketResponse:
    if payload.status is None and payload.priority is None and payload.assignee_id is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    current = fetch_one(conn, "SELECT status FROM tickets WHERE id = ?", (ticket_id,))
    if current is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

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

    assignments: list[str] = []
    params: list[object] = []
    if payload.status is not None:
        assignments.append("status = ?")
        params.append(payload.status.value)
    if payload.priority is not None:
        assignments.append("priority = ?")
        params.append(payload.priority.value)
    if payload.assignee_id is not None:
        assignments.append("assignee_id = ?")
        params.append(payload.assignee_id)
    assignments.append("updated_at = ?")
    params.extend([utc_now_iso(), ticket_id])

    with transaction(conn):
        run(conn, f"UPDATE tickets SET {', '.join(assignments)} WHERE id = ?", params)

    row = fetch_one(conn, f"{TICKET_SELECT} WHERE t.id = ?", (ticket_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse.model_validate(dict(row))


@router.post("/{ticket_id}/comments", status_code=201)
async def add_comment(
    ticket_id: int, payload: CommentCreate, user: CurrentUser, conn: DbConnection
) -> CommentResponse:
    ticket = fetch_one(conn, "SELECT id FROM tickets WHERE id = ?", (ticket_id,))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

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
