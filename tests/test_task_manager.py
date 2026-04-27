from webapp.db import init_db
from webapp.repository import Repository
from webapp.task_manager import TaskManager


def test_task_manager_runs_a_queued_task(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    manager = TaskManager(repo)

    monkeypatch.setattr(
        "webapp.task_manager.run_workflow_once",
        lambda request, on_event: {
            "mode": request.mode,
            "email": "done@example.com",
            "ott": "ott$masked",
        },
    )

    task_id = repo.create_task(mode="full", payload={"account_count": 1})
    manager.run_next_once()
    task = repo.get_task(task_id)

    assert task["status"] == "succeeded"
    assert task["result"]["email"] == "done@example.com"


def test_task_manager_wake_processes_queue_in_background(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    manager = TaskManager(repo)

    monkeypatch.setattr(
        "webapp.task_manager.run_workflow_once",
        lambda request, on_event: {"mode": request.mode, "email": "bg@example.com", "ott": "ott$bg"},
    )

    task_id = repo.create_task(mode="full", payload={"account_count": 1})
    manager.wake()

    deadline = __import__("time").time() + 2
    while __import__("time").time() < deadline:
        task = repo.get_task(task_id)
        if task["status"] == "succeeded":
            break
        __import__("time").sleep(0.05)

    task = repo.get_task(task_id)
    assert task["status"] == "succeeded"
    assert task["result"]["email"] == "bg@example.com"
