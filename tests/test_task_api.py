from fastapi.testclient import TestClient
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
