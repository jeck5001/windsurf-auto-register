from fastapi.testclient import TestClient

from webapp.app import app


def test_dashboard_page_renders_navigation():
    client = TestClient(app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Tasks" in response.text
    assert "Accounts" in response.text
    assert "Settings" in response.text
