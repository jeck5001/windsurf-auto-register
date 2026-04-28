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


def test_task_manager_updates_existing_account_for_manual_trial_and_push(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    manager = TaskManager(repo)
    repo.save_account_result(
        task_id=1,
        mode="full",
        result={"email": "account@example.com", "ott": ""},
    )
    account_id = repo.list_accounts()[0]["id"]

    def fake_run(request, on_event):
        if request.mode == "trial":
            return {
                "mode": "trial",
                "email": request.email,
                "trial_checkout_url": "https://checkout.stripe.com/manual",
            }
        return {
            "mode": "upload",
            "ott": "ott$plain",
            "pool_result": {"account": {"status": "active"}},
        }

    monkeypatch.setattr("webapp.task_manager.run_workflow_once", fake_run)

    trial_task_id = repo.create_task(
        mode="trial",
        payload={"account_id": account_id, "email": "account@example.com", "password": "SecretPass123"},
    )
    manager.run_next_once()
    push_task_id = repo.create_task(
        mode="upload",
        payload={"account_id": account_id, "ott": "ott$plain", "label": "manual-label"},
    )
    manager.run_next_once()

    account = repo.get_account(account_id)
    assert repo.get_task(trial_task_id)["status"] == "succeeded"
    assert repo.get_task(push_task_id)["status"] == "succeeded"
    assert account["trial_checkout_url"] == "https://checkout.stripe.com/manual"
    assert account["pool_status"] == "active"
    assert account["ott"] == "ott$plain"


def test_task_manager_saves_each_account_from_batch_full_result(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    init_db(db_path)
    repo = Repository(db_path)
    manager = TaskManager(repo)

    monkeypatch.setattr(
        "webapp.task_manager.run_workflow_once",
        lambda request, on_event: {
            "mode": "batch",
            "requested_count": 2,
            "success_count": 2,
            "failure_count": 0,
            "accounts": [
                {
                    "mode": "full",
                    "email": "first@example.com",
                    "ott": "ott$first",
                    "session_token": "session-first",
                    "pool_result": {"account": {"status": "active"}},
                },
                {
                    "mode": "full",
                    "email": "second@example.com",
                    "ott": "ott$second",
                    "session_token": "session-second",
                    "pool_result": {"account": {"status": "paused"}},
                },
            ],
            "failures": [],
        },
    )

    task_id = repo.create_task(mode="full", payload={"account_count": 2})
    manager.run_next_once()

    accounts = repo.list_accounts(limit=10)
    assert repo.get_task(task_id)["status"] == "succeeded"
    assert [account["email"] for account in accounts] == ["second@example.com", "first@example.com"]
    assert accounts[0]["ott"] == "ott$second"
    assert accounts[0]["session_token"] == "session-second"
    assert accounts[1]["ott"] == "ott$first"
    assert accounts[1]["session_token"] == "session-first"
