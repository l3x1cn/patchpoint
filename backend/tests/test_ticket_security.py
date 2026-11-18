from contextlib import closing
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, transaction, utc_now_iso
from app.routers.tickets import COMMENTS_IN_DETAIL_MAX
from app.schemas import MAX_SQLITE_INTEGER, Role
from tests.support import LoginAs, TicketFactory, UserFactory, log_events

OUT_OF_RANGE_ID = 99999999999999999999


def ids(response_json: list[dict[str, Any]]) -> list[int]:
    return [ticket["id"] for ticket in response_json]


@pytest.mark.parametrize(
    "term",
    [
        "') OR 1=1 OR ('",
        "' UNION SELECT token_hash, 1 FROM sessions --",
        "O'Brien",
    ],
)
def test_search_input_is_not_interpreted_as_sql(
    user_factory: UserFactory,
    login_as: LoginAs,
    ticket_factory: TicketFactory,
    term: str,
) -> None:
    user_factory("jan")
    user_factory("anna")
    ticket_factory(login_as("anna"), title="Cudze zgłoszenie")
    jan = login_as("jan")
    ticket_factory(jan, title="Własne zgłoszenie")

    response = jan.get("/api/tickets", params={"search": term})

    assert response.status_code == 200
    assert response.json() == []


def test_search_treats_like_wildcards_literally(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    jan = login_as("jan")
    percent = ticket_factory(jan, title="Zużycie 100% baterii")
    underscore = ticket_factory(jan, title="Plik raport_final", description="Brak")
    ticket_factory(jan, title="Zwykłe zgłoszenie", description="Brak")

    percent_hits = jan.get("/api/tickets", params={"search": "%"}).json()
    underscore_hits = jan.get("/api/tickets", params={"search": "_"}).json()

    assert ids(percent_hits) == [percent]
    assert ids(underscore_hits) == [underscore]


def test_employee_cannot_read_foreign_ticket(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    user_factory("anna")
    foreign = ticket_factory(login_as("anna"))

    response = login_as("jan").get(f"/api/tickets/{foreign}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_employee_cannot_comment_on_foreign_ticket(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    user_factory("anna")
    user_factory("agent", role=Role.AGENT)
    foreign = ticket_factory(login_as("anna"))

    response = login_as("jan").post(f"/api/tickets/{foreign}/comments", json={"body": "Intruz"})

    detail = login_as("agent").get(f"/api/tickets/{foreign}").json()
    assert response.status_code == 404
    assert detail["comments"] == []


def test_agent_can_read_any_ticket(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    user_factory("agent", role=Role.AGENT)
    ticket_id = ticket_factory(login_as("jan"))

    response = login_as("agent").get(f"/api/tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_foreign_ticket_access_is_logged(
    user_factory: UserFactory,
    login_as: LoginAs,
    ticket_factory: TicketFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    jan_id = user_factory("jan")
    user_factory("anna")
    foreign = ticket_factory(login_as("anna"))

    login_as("jan").get(f"/api/tickets/{foreign}")

    denied = [e for e in log_events(caplog) if e["event"] == "access_denied"]
    assert len(denied) == 1
    assert denied[0]["reason"] == "not_ticket_owner"
    assert denied[0]["ticket_id"] == foreign
    assert denied[0]["user_id"] == jan_id


def test_out_of_range_ids_are_rejected(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    user_factory("agent", role=Role.AGENT)
    ticket_id = ticket_factory(login_as("jan"))
    agent = login_as("agent")

    statuses = [
        agent.get(f"/api/tickets/{OUT_OF_RANGE_ID}").status_code,
        agent.patch(f"/api/tickets/{OUT_OF_RANGE_ID}", json={"status": "closed"}).status_code,
        agent.post(f"/api/tickets/{OUT_OF_RANGE_ID}/comments", json={"body": "x"}).status_code,
        agent.patch(
            f"/api/tickets/{ticket_id}", json={"assignee_id": MAX_SQLITE_INTEGER + 1}
        ).status_code,
        agent.get("/api/tickets/0").status_code,
    ]

    assert statuses == [422, 422, 422, 422, 422]


def test_ticket_list_is_paginated(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    jan = login_as("jan")
    oldest = ticket_factory(jan, title="Pierwsze")
    middle = ticket_factory(jan, title="Drugie")
    newest = ticket_factory(jan, title="Trzecie")

    first_page = jan.get("/api/tickets", params={"limit": 2}).json()
    second_page = jan.get("/api/tickets", params={"limit": 2, "offset": 2}).json()

    assert ids(first_page) == [newest, middle]
    assert ids(second_page) == [oldest]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"search": "x" * 101},
    ],
)
def test_pagination_bounds_are_validated(
    user_factory: UserFactory, login_as: LoginAs, params: dict[str, int | str]
) -> None:
    user_factory("jan")

    response = login_as("jan").get("/api/tickets", params=params)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "override",
    [
        {"title": "t" * 201},
        {"description": "d" * 5001},
        {"asset_tag": "a" * 51},
        {"location": "l" * 101},
    ],
)
def test_ticket_text_fields_have_length_limits(
    user_factory: UserFactory, login_as: LoginAs, override: dict[str, str]
) -> None:
    user_factory("jan")
    payload = {"title": "Tytuł", "description": "Opis", "category": "other", **override}

    response = login_as("jan").post("/api/tickets", json=payload)

    assert response.status_code == 422


def test_comment_body_has_length_limit(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    jan = login_as("jan")
    ticket_id = ticket_factory(jan)

    response = jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "c" * 2001})

    assert response.status_code == 422


def test_ticket_detail_returns_only_newest_comments_with_total(
    user_factory: UserFactory,
    login_as: LoginAs,
    ticket_factory: TicketFactory,
    settings: Settings,
) -> None:
    author_id = user_factory("jan")
    jan = login_as("jan")
    ticket_id = ticket_factory(jan)
    total = COMMENTS_IN_DETAIL_MAX + 25
    with closing(connect(settings.database_path)) as conn, transaction(conn):
        conn.executemany(
            "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
            [(ticket_id, author_id, f"komentarz {n}", utc_now_iso()) for n in range(1, total + 1)],
        )

    response = jan.get(f"/api/tickets/{ticket_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["comment_count"] == total
    assert [c["body"] for c in body["comments"]] == [
        f"komentarz {n}" for n in range(total - COMMENTS_IN_DETAIL_MAX + 1, total + 1)
    ]


def test_ticket_detail_counts_all_comments_below_the_limit(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    jan = login_as("jan")
    ticket_id = ticket_factory(jan)
    jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "Pierwszy"})
    jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "Drugi"})

    body = jan.get(f"/api/tickets/{ticket_id}").json()

    assert body["comment_count"] == 2
    assert [c["body"] for c in body["comments"]] == ["Pierwszy", "Drugi"]


def test_unknown_fields_are_rejected(
    user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
) -> None:
    user_factory("jan")
    user_factory("agent", role=Role.AGENT)
    jan = login_as("jan")
    agent = login_as("agent")
    ticket_id = ticket_factory(jan)

    create = jan.post(
        "/api/tickets",
        json={"title": "T", "description": "D", "category": "other", "status": "closed"},
    )
    update = agent.patch(f"/api/tickets/{ticket_id}", json={"reporter_id": 1})
    comment = jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "x", "author_id": 1})

    assert [create.status_code, update.status_code, comment.status_code] == [422, 422, 422]


def test_ticket_updates_are_audited(
    user_factory: UserFactory,
    login_as: LoginAs,
    ticket_factory: TicketFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_factory("jan")
    agent_id = user_factory("agent", role=Role.AGENT)
    ticket_id = ticket_factory(login_as("jan"))

    response = login_as("agent").patch(f"/api/tickets/{ticket_id}", json={"status": "in_progress"})

    assert response.status_code == 200
    updated = [e for e in log_events(caplog) if e["event"] == "ticket_updated"]
    assert len(updated) == 1
    assert updated[0]["user_id"] == agent_id
    assert updated[0]["ticket_id"] == ticket_id
    assert updated[0]["status"] == "in_progress"
    assert updated[0]["priority"] is None
    assert updated[0]["assignee_id"] is None


def test_employee_role_denial_is_logged(
    user_factory: UserFactory,
    login_as: LoginAs,
    ticket_factory: TicketFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    jan_id = user_factory("jan")
    jan: TestClient = login_as("jan")
    ticket_id = ticket_factory(jan)

    response = jan.patch(f"/api/tickets/{ticket_id}", json={"status": "closed"})

    denied = [e for e in log_events(caplog) if e["event"] == "access_denied"]
    assert response.status_code == 403
    assert len(denied) == 1
    assert denied[0]["reason"] == "agent_role_required"
    assert denied[0]["user_id"] == jan_id
