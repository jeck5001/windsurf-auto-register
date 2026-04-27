from fastapi.testclient import TestClient

from webapp.app import app
from webapp.db import init_db
from webapp.repository import Repository


def test_dashboard_page_renders_navigation():
    client = TestClient(app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Tasks" in response.text
    assert "Accounts" in response.text
    assert "Settings" in response.text


def test_dashboard_shows_stats_from_repository(tmp_path):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    repo.create_task(mode="full", payload={"account_count": 1})
    app.state.repository = repo

    client = TestClient(app)
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Queued Tasks" in response.text
    assert "Recent Events" in response.text


def test_accounts_and_settings_pages_show_live_data(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    repo.save_account_result(
        task_id=1,
        mode="full",
        result={
            "email": "account@example.com",
            "ott": "ott$masked",
            "trial_checkout_url": "https://checkout.stripe.com/test",
            "pool_result": {"account": {"status": "active"}},
        },
    )
    app.state.repository = repo
    monkeypatch.setenv("YYDS_MAIL_API_KEY", "secret-key")

    client = TestClient(app)
    accounts_response = client.get("/accounts")
    settings_response = client.get("/settings")

    assert accounts_response.status_code == 200
    assert "account@example.com" in accounts_response.text
    assert settings_response.status_code == 200
    assert "configured" in settings_response.text


def test_accounts_page_syncs_pool_accounts_into_local_repository(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    app.state.repository = repo

    class FakePoolClient:
        def list_accounts(self):
            return [
                {"id": "pool-1", "email": "legacy@example.com", "status": "active"},
                {"id": "pool-2", "email": "other@example.com", "status": "paused"},
            ]

    app.state.pool_client = FakePoolClient()

    client = TestClient(app)
    response = client.get("/accounts")
    second_response = client.get("/accounts")

    assert response.status_code == 200
    assert second_response.status_code == 200
    assert "legacy@example.com" in response.text
    assert "other@example.com" in response.text
    rows = repo.list_accounts(limit=10)
    assert [row["email"] for row in rows] == ["other@example.com", "legacy@example.com"]


def test_tasks_page_shows_docker_runtime_notice(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    monkeypatch.setenv("WINDSURF_ADMIN_DB_PATH", str(tmp_path / "admin.db"))

    with TestClient(app) as client:
        response = client.get("/tasks")

    assert response.status_code == 200
    assert "Docker runtime does not support browser automation flows in v1" in response.text
