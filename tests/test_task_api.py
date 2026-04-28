from fastapi.testclient import TestClient
import asyncio
import time

from webapp.app import app


def test_create_task_api_enqueues_full_run(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            json={
                "mode": "full",
                "email": "",
                "password": "",
                "account_count": 2,
                "generate_trial_link": False,
            },
        )

        assert response.status_code == 201
        assert response.json()["status"] == "queued"


def test_retry_and_stop_endpoints_return_control_states(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        task_id = repo.create_task(mode="full", payload={"account_count": 1})

        stop_response = client.post(f"/api/tasks/{task_id}/stop")
        retry_response = client.post(f"/api/tasks/{task_id}/retry")

        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stop_requested"
        assert retry_response.status_code == 201
        assert retry_response.json()["status"] == "queued"


def test_task_events_endpoint_returns_sse(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        task_id = repo.create_task(mode="full", payload={"account_count": 1})
        repo.add_event(task_id, "info", "task created")

        response = client.get(f"/api/tasks/{task_id}/events")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "task created" in response.text


def test_create_task_api_rejects_generate_trial_link_in_docker(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    monkeypatch.setenv("WINDSURF_ADMIN_DB_PATH", str(tmp_path / "admin.db"))

    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            json={
                "mode": "full",
                "email": "",
                "password": "",
                "account_count": 1,
                "generate_trial_link": True,
            },
        )

        assert response.status_code == 201
        task_id = response.json()["id"]

        deadline = time.time() + 2
        while time.time() < deadline:
            task = app.state.repository.get_task(task_id)
            if task["status"] == "failed":
                break
            time.sleep(0.05)

        task = app.state.repository.get_task(task_id)
        assert task["status"] == "failed"

        events = client.get(f"/api/tasks/{task_id}/events")
        assert "Docker runtime does not support browser automation flows in v1" in events.text


def test_account_update_and_delete_api_manage_local_accounts(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={
                "email": "old@example.com",
                "trial_checkout_url": "https://checkout.stripe.com/old",
                "pool_result": {"account": {"status": "active"}},
            },
        )
        account_id = repo.list_accounts()[0]["id"]

        update_response = client.patch(
            f"/api/accounts/{account_id}",
            json={
                "email": "new@example.com",
                "pool_status": "paused",
                "trial_checkout_url": "https://checkout.stripe.com/new",
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["account"]["email"] == "new@example.com"
        assert update_response.json()["account"]["pool_status"] == "paused"

        delete_response = client.delete(f"/api/accounts/{account_id}")

        assert delete_response.status_code == 200
        assert delete_response.json() == {"ok": True, "account_id": account_id}
        assert repo.list_accounts() == []


def test_account_trial_api_generates_link_for_existing_account(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={"email": "account@example.com", "session_token": "session-plain"},
        )
        account_id = repo.list_accounts()[0]["id"]
        monkeypatch.setattr(
            "webapp.routes_api.run_workflow_once",
            lambda workflow_request, on_event: {
                "mode": "trial",
                "email": workflow_request.email,
                "session_token": workflow_request.session_token,
                "trial_checkout_url": "https://checkout.stripe.com/direct",
            },
        )

        response = client.post(
            f"/api/accounts/{account_id}/trial",
            json={},
        )

        assert response.status_code == 200
        assert response.json()["account"]["trial_checkout_url"] == "https://checkout.stripe.com/direct"
        assert repo.get_account(account_id)["trial_checkout_url"] == "https://checkout.stripe.com/direct"


def test_account_trial_api_rejects_without_stored_session_token(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="pool-sync",
            result={"email": "account@example.com"},
        )
        account_id = repo.list_accounts()[0]["id"]

        response = client.post(
            f"/api/accounts/{account_id}/trial",
            json={},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "No stored session token available for direct Trial"


def test_account_push_api_pushes_existing_account(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={"email": "account@example.com", "ott": "ott$plain"},
        )
        account_id = repo.list_accounts()[0]["id"]
        monkeypatch.setattr(
            "webapp.routes_api.run_workflow_once",
            lambda workflow_request, on_event: {
                "mode": "upload",
                "ott": workflow_request.ott,
                "pool_result": {"account": {"status": "active"}},
            },
        )

        response = client.post(
            f"/api/accounts/{account_id}/push",
            json={},
        )

        assert response.status_code == 200
        assert response.json()["account"]["ott"] == "ott$plain"
        assert response.json()["account"]["pool_status"] == "active"
        assert repo.get_account(account_id)["pool_status"] == "active"


def test_account_push_api_rejects_without_full_ott(tmp_path):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={"email": "account@example.com", "ott": "ott$masked...tail"},
        )
        account_id = repo.list_accounts()[0]["id"]

        response = client.post(
            f"/api/accounts/{account_id}/push",
            json={},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "No stored full OTT available for direct Push"


def test_account_trial_api_runs_workflow_off_event_loop(tmp_path, monkeypatch):
    app.state.db_path = tmp_path / "admin.db"

    with TestClient(app) as client:
        repo = app.state.repository
        repo.save_account_result(
            task_id=1,
            mode="full",
            result={"email": "account@example.com", "session_token": "session-plain"},
        )
        account_id = repo.list_accounts()[0]["id"]

        def fake_run(workflow_request, on_event):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                raise AssertionError("run_workflow_once should not run on the request event loop")
            return {
                "mode": "trial",
                "email": workflow_request.email,
                "session_token": workflow_request.session_token,
                "trial_checkout_url": "https://checkout.stripe.com/direct",
            }

        monkeypatch.setattr("webapp.routes_api.run_workflow_once", fake_run)

        response = client.post(
            f"/api/accounts/{account_id}/trial",
            json={},
        )

        assert response.status_code == 200
        assert response.json()["account"]["trial_checkout_url"] == "https://checkout.stripe.com/direct"
