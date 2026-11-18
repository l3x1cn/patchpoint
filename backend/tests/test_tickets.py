import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import Role
from tests.support import API_BASE_URL, DEMO_PASSWORD, LoginAs, TicketFactory, UserFactory


def patch_status(agent: TestClient, ticket_id: int, status: str) -> int:
    return agent.patch(f"/api/tickets/{ticket_id}", json={"status": status}).status_code


class TestCreateTicket:
    def test_employee_creates_open_ticket(
        self, user_factory: UserFactory, login_as: LoginAs
    ) -> None:
        user_id = user_factory("jan", full_name="Jan K.")
        jan = login_as("jan")

        response = jan.post(
            "/api/tickets",
            json={
                "title": "Mysz nie działa",
                "description": "Kursor się nie porusza.",
                "category": "peripheral",
                "asset_tag": "MSE-1",
                "location": "B-1",
            },
        )

        body = response.json()
        assert response.status_code == 201
        assert body["status"] == "open"
        assert body["priority"] == "medium"
        assert body["reporter_id"] == user_id
        assert body["reporter_name"] == "Jan K."
        assert body["assignee_id"] is None
        assert body["asset_tag"] == "MSE-1"

    def test_requires_session(self, client: TestClient) -> None:
        response = client.post(
            "/api/tickets",
            json={"title": "x", "description": "y", "category": "laptop"},
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "override",
        [{"category": "toaster"}, {"priority": "urgent"}, {"title": ""}],
    )
    def test_validation(
        self, user_factory: UserFactory, login_as: LoginAs, override: dict[str, str]
    ) -> None:
        user_factory("jan")
        jan = login_as("jan")
        payload = {"title": "T", "description": "D", "category": "laptop"} | override

        response = jan.post("/api/tickets", json=payload)

        assert response.status_code == 422


class TestListTickets:
    def test_employee_sees_only_own_tickets(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        user_factory("anna")
        jan = login_as("jan")
        anna = login_as("anna")
        own_id = ticket_factory(jan, title="Jana")
        ticket_factory(anna, title="Anny")

        response = jan.get("/api/tickets")

        assert response.status_code == 200
        assert [t["id"] for t in response.json()] == [own_id]

    def test_agent_sees_all_tickets_newest_first(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        user_factory("anna")
        user_factory("agent", role=Role.AGENT)
        first = ticket_factory(login_as("jan"))
        second = ticket_factory(login_as("anna"))
        agent = login_as("agent")

        response = agent.get("/api/tickets")

        assert response.status_code == 200
        assert [t["id"] for t in response.json()] == [second, first]

    def test_status_filter(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        user_factory("agent", role=Role.AGENT)
        jan = login_as("jan")
        agent = login_as("agent")
        ticket_factory(jan)
        moved = ticket_factory(jan)
        assert patch_status(agent, moved, "in_progress") == 200

        response = agent.get("/api/tickets", params={"status": "in_progress"})

        assert [t["id"] for t in response.json()] == [moved]

    @pytest.mark.parametrize(
        ("term", "title", "description"),
        [
            ("MONITOR", "Monitor flickers", "Screen blinks"),
            ("toner", "Printer is faint", "The Toner cartridge seems empty"),
        ],
    )
    def test_search_matches_title_and_description_case_insensitively(
        self,
        user_factory: UserFactory,
        login_as: LoginAs,
        ticket_factory: TicketFactory,
        term: str,
        title: str,
        description: str,
    ) -> None:
        user_factory("jan")
        jan = login_as("jan")
        ticket_factory(jan, title="Unrelated", description="Nothing here")
        expected = ticket_factory(jan, title=title, description=description)

        response = jan.get("/api/tickets", params={"search": term})

        assert [t["id"] for t in response.json()] == [expected]


class TestTicketDetail:
    def test_includes_comments_with_author_name(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan", full_name="Jan K.")
        jan = login_as("jan")
        ticket_id = ticket_factory(jan)
        jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "Pilne"})

        response = jan.get(f"/api/tickets/{ticket_id}")

        body = response.json()
        assert response.status_code == 200
        assert body["id"] == ticket_id
        assert [(c["author_name"], c["body"]) for c in body["comments"]] == [("Jan K.", "Pilne")]

    def test_unknown_ticket(self, user_factory: UserFactory, login_as: LoginAs) -> None:
        user_factory("jan")

        response = login_as("jan").get("/api/tickets/9999")

        assert response.status_code == 404


class TestUpdateTicket:
    @pytest.mark.parametrize(
        "path",
        [
            ["in_progress"],
            ["in_progress", "resolved"],
            ["in_progress", "resolved", "closed"],
            ["closed"],
            ["in_progress", "open"],
            ["in_progress", "resolved", "in_progress"],
        ],
    )
    def test_allowed_paths(
        self,
        user_factory: UserFactory,
        login_as: LoginAs,
        ticket_factory: TicketFactory,
        path: list[str],
    ) -> None:
        user_factory("jan")
        user_factory("agent", role=Role.AGENT)
        ticket_id = ticket_factory(login_as("jan"))
        agent = login_as("agent")

        for status in path:
            response = agent.patch(f"/api/tickets/{ticket_id}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

        assert agent.get(f"/api/tickets/{ticket_id}").json()["status"] == path[-1]

    @pytest.mark.parametrize(
        ("setup", "target"),
        [
            ([], "resolved"),
            (["closed"], "open"),
            (["closed"], "in_progress"),
        ],
    )
    def test_forbidden_transitions(
        self,
        user_factory: UserFactory,
        login_as: LoginAs,
        ticket_factory: TicketFactory,
        setup: list[str],
        target: str,
    ) -> None:
        user_factory("jan")
        user_factory("agent", role=Role.AGENT)
        ticket_id = ticket_factory(login_as("jan"))
        agent = login_as("agent")
        for status in setup:
            assert patch_status(agent, ticket_id, status) == 200

        response = agent.patch(f"/api/tickets/{ticket_id}", json={"status": target})

        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]

    def test_employee_cannot_update(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        jan = login_as("jan")
        ticket_id = ticket_factory(jan)

        response = jan.patch(f"/api/tickets/{ticket_id}", json={"status": "closed"})

        assert response.status_code == 403

    def test_assign_agent(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        agent_id = user_factory("agent", role=Role.AGENT, full_name="Agent A")
        ticket_id = ticket_factory(login_as("jan"))

        response = login_as("agent").patch(
            f"/api/tickets/{ticket_id}", json={"assignee_id": agent_id, "priority": "critical"}
        )

        body = response.json()
        assert response.status_code == 200
        assert body["assignee_id"] == agent_id
        assert body["assignee_name"] == "Agent A"
        assert body["priority"] == "critical"

    @pytest.mark.parametrize("target", ["employee", "missing"])
    def test_assignee_must_be_agent(
        self,
        user_factory: UserFactory,
        login_as: LoginAs,
        ticket_factory: TicketFactory,
        target: str,
    ) -> None:
        employee_id = user_factory("jan")
        user_factory("agent", role=Role.AGENT)
        ticket_id = ticket_factory(login_as("jan"))
        assignee_id = employee_id if target == "employee" else 9999

        response = login_as("agent").patch(
            f"/api/tickets/{ticket_id}", json={"assignee_id": assignee_id}
        )

        assert response.status_code == 400

    def test_empty_update(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        user_factory("agent", role=Role.AGENT)
        ticket_id = ticket_factory(login_as("jan"))

        response = login_as("agent").patch(f"/api/tickets/{ticket_id}", json={})

        assert response.status_code == 400

    def test_unknown_ticket(self, user_factory: UserFactory, login_as: LoginAs) -> None:
        user_factory("agent", role=Role.AGENT)

        response = login_as("agent").patch("/api/tickets/9999", json={"status": "closed"})

        assert response.status_code == 404

    def test_partial_update_keeps_other_fields(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        agent_id = user_factory("agent", role=Role.AGENT)
        ticket_id = ticket_factory(login_as("jan"))
        agent = login_as("agent")
        assert patch_status(agent, ticket_id, "in_progress") == 200
        assigned = agent.patch(f"/api/tickets/{ticket_id}", json={"assignee_id": agent_id})
        assert assigned.status_code == 200

        response = agent.patch(f"/api/tickets/{ticket_id}", json={"priority": "low"})

        body = response.json()
        assert response.status_code == 200
        assert body["priority"] == "low"
        assert body["status"] == "in_progress"
        assert body["assignee_id"] == agent_id


class TestComments:
    def test_add_comment(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("agent", role=Role.AGENT, full_name="Agent A")
        user_factory("jan")
        ticket_id = ticket_factory(login_as("jan"))
        agent = login_as("agent")

        response = agent.post(f"/api/tickets/{ticket_id}/comments", json={"body": "Sprawdzam"})

        assert response.status_code == 201
        assert response.json()["author_name"] == "Agent A"
        comments = agent.get(f"/api/tickets/{ticket_id}").json()["comments"]
        assert [c["body"] for c in comments] == ["Sprawdzam"]

    def test_unknown_ticket(self, user_factory: UserFactory, login_as: LoginAs) -> None:
        user_factory("jan")

        response = login_as("jan").post("/api/tickets/9999/comments", json={"body": "x"})

        assert response.status_code == 404

    def test_empty_body(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        jan = login_as("jan")
        ticket_id = ticket_factory(jan)

        response = jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": ""})

        assert response.status_code == 422

    def test_add_comment_updates_ticket_timestamp(
        self, user_factory: UserFactory, login_as: LoginAs, ticket_factory: TicketFactory
    ) -> None:
        user_factory("jan")
        jan = login_as("jan")
        ticket_id = ticket_factory(jan)
        before = jan.get(f"/api/tickets/{ticket_id}").json()["updated_at"]

        response = jan.post(f"/api/tickets/{ticket_id}/comments", json={"body": "Pilne"})

        after = jan.get(f"/api/tickets/{ticket_id}").json()["updated_at"]
        assert response.status_code == 201
        assert after >= before


class TestSeededTickets:
    def test_demo_tickets(self, seeded_settings: Settings) -> None:
        with TestClient(create_app(seeded_settings), base_url=API_BASE_URL) as seeded:
            jan_login = seeded.post(
                "/api/auth/login", json={"username": "jan.kowalski", "password": DEMO_PASSWORD}
            )
            jan_tickets = seeded.get("/api/tickets").json()
            agent_login = seeded.post(
                "/api/auth/login", json={"username": "helpdesk", "password": DEMO_PASSWORD}
            )
            all_tickets = seeded.get("/api/tickets").json()
            printer = next(t for t in all_tickets if t["title"] == "Drukarka zacina papier")
            detail = seeded.get(f"/api/tickets/{printer['id']}").json()

        assert jan_login.status_code == 200
        assert agent_login.status_code == 200
        assert len(jan_tickets) == 2
        assert len(all_tickets) == 3
        assert detail["status"] == "in_progress"
        assert detail["assignee_name"] == "Piotr Serwisant"
        assert len(detail["comments"]) == 1
