from fastapi.testclient import TestClient

FRONTEND_ORIGIN = "http://localhost:5500"


def test_preflight_allows_frontend_origin_with_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/auth/me",
        headers={"Origin": FRONTEND_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
