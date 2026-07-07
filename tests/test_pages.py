import re

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
    assert '/static/admin.css?v=' in response.text
    assert '/static/admin.js?v=' in response.text


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
    trial_url = "https://checkout.stripe.com/test"
    repo.save_account_result(
        task_id=1,
        mode="full",
        result={
            "email": "account@example.com",
            "password": "StoredPass123",
            "ott": "ott$masked",
            "trial_checkout_url": trial_url,
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
    assert "Password" in accounts_response.text
    assert re.search(r"<td>\s*StoredPass123\s*</td>", accounts_response.text)
    assert f'href="{trial_url}"' in accounts_response.text
    assert 'data-copy-text="' in accounts_response.text
    assert "Open" in accounts_response.text
    assert "Copy" in accounts_response.text
    assert 'data-account-edit-button="' in accounts_response.text
    assert 'data-account-trial-button="' in accounts_response.text
    assert 'data-account-push-button="' in accounts_response.text
    assert 'data-account-delete-button="' in accounts_response.text
    assert 'id="account-modal"' in accounts_response.text
    assert 'id="modal-password"' in accounts_response.text
    assert 'id="modal-session-token"' in accounts_response.text
    assert 'data-modal-trial' not in accounts_response.text
    assert 'data-modal-push' not in accounts_response.text
    assert settings_response.status_code == 200
    assert "configured" in settings_response.text


def test_accounts_page_supports_language_switch(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    app.state.repository = repo
    monkeypatch.setattr(app.state, "pool_client", None, raising=False)

    client = TestClient(app)
    response = client.get("/accounts?lang=zh")

    assert response.status_code == 200
    assert 'lang="zh"' in response.text
    assert "账号" in response.text
    assert "English" in response.text
    assert "中文" in response.text


def test_accounts_page_paginates_accounts_and_shows_total_count(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    for index in range(55):
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={
                "email": f"account-{index:02d}@example.com",
                "password": f"Pass{index:02d}",
            },
        )
    app.state.repository = repo
    monkeypatch.setattr(app.state, "pool_client", None, raising=False)

    client = TestClient(app)
    response = client.get("/accounts")
    second_response = client.get("/accounts?page=2")

    assert response.status_code == 200
    assert second_response.status_code == 200
    assert "55 accounts" in response.text
    assert "Page 1 of 2" in response.text
    assert 'href="/accounts?page=2"' in response.text
    assert "account-54@example.com" in response.text
    assert "account-05@example.com" in response.text
    assert "account-04@example.com" not in response.text
    assert "55 accounts" in second_response.text
    assert "Page 2 of 2" in second_response.text
    assert 'href="/accounts?page=1"' in second_response.text
    assert "account-04@example.com" in second_response.text
    assert "account-00@example.com" in second_response.text
    assert "account-54@example.com" not in second_response.text


def test_accounts_page_syncs_pool_accounts_into_local_repository(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    app.state.repository = repo

    class FakePoolClient:
        def list_accounts(self):
            return [
                {
                    "id": "pool-1",
                    "email": "legacy@example.com",
                    "password": "SyncedPass123",
                    "status": "active",
                },
                {"id": "pool-2", "email": "other@example.com", "status": "paused"},
            ]

    app.state.pool_client = FakePoolClient()

    client = TestClient(app)
    response = client.get("/accounts")
    second_response = client.get("/accounts")

    assert response.status_code == 200
    assert second_response.status_code == 200
    assert "legacy@example.com" in response.text
    assert "SyncedPass123" in response.text
    assert "other@example.com" in response.text
    rows = repo.list_accounts(limit=10)
    assert [row["email"] for row in rows] == ["other@example.com", "legacy@example.com"]
    assert rows[1]["password"] == "SyncedPass123"


def test_deleted_synced_account_is_not_reimported_from_pool(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    repo.upsert_pool_account(email="legacy@example.com", pool_status="active")
    account_id = repo.list_accounts()[0]["id"]
    repo.delete_account(account_id)
    app.state.repository = repo

    class FakePoolClient:
        def list_accounts(self):
            return [{"id": "pool-1", "email": "legacy@example.com", "status": "active"}]

    app.state.pool_client = FakePoolClient()

    client = TestClient(app)
    response = client.get("/accounts")

    assert response.status_code == 200
    assert "legacy@example.com" not in response.text
    assert repo.list_accounts(limit=10) == []


def test_accounts_page_surfaces_pool_sync_errors(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    app.state.repository = repo

    class FakePoolClient:
        def list_accounts(self):
            raise RuntimeError("pool unavailable")

    app.state.pool_client = FakePoolClient()

    client = TestClient(app)
    response = client.get("/accounts")

    assert response.status_code == 200
    assert "Pool sync failed: pool unavailable" in response.text


def test_tasks_page_shows_docker_runtime_notice(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    monkeypatch.setenv("WINDSURF_ADMIN_DB_PATH", str(tmp_path / "admin.db"))

    with TestClient(app) as client:
        response = client.get("/tasks")

    assert response.status_code == 200
    assert "Docker runtime does not support browser automation flows in v1" in response.text
    assert "Leave email and password blank in full mode to auto-generate them." in response.text
    assert 'autocomplete="off"' in response.text
    assert 'name="task_email"' in response.text
    assert 'name="task_password"' in response.text
    assert 'autocomplete="new-password"' in response.text


def test_tasks_page_shows_recent_tasks(tmp_path):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    repo.create_task(mode="trial", payload={"email": "account@example.com", "password": "SecretPass123"})
    app.state.repository = repo

    client = TestClient(app)
    response = client.get("/tasks")

    assert response.status_code == 200
    assert "trial" in response.text
    assert "queued" in response.text
