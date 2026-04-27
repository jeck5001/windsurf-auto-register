from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from windsurf_auth_replay import request_stop

from webapp.repository import Repository
from webapp.workflow_runner import WorkflowRequest, run_workflow_once


@dataclass
class TaskManager:
    repo: Repository
    paused: bool = False
    current_task_id: int | None = None

    def run_next_once(self) -> None:
        if self.paused:
            return
        task = self.repo.get_next_queued_task()
        if not task:
            return

        task_id = int(task["id"])
        self.current_task_id = task_id
        payload: dict[str, Any] = json.loads(task["payload_json"])
        self.repo.mark_running(task_id)

        def on_event(event: dict[str, str]) -> None:
            self.repo.add_event(task_id, event["level"], event["message"])

        request = WorkflowRequest(
            mode=task["mode"],
            email=payload.get("email", ""),
            password=payload.get("password", ""),
            account_count=payload.get("account_count", 1),
            generate_trial_link=payload.get("generate_trial_link", False),
        )
        try:
            result = run_workflow_once(request, on_event=on_event)
            self.repo.mark_succeeded(task_id, result)
            self.repo.save_account_result(task_id, task["mode"], result)
        except Exception as exc:
            self.repo.mark_failed(task_id, str(exc))
        finally:
            self.current_task_id = None

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def wake(self) -> None:
        return None

    def stop(self, task_id: int) -> None:
        if self.current_task_id == task_id:
            request_stop()
        else:
            self.repo.cancel_queued_task(task_id)
