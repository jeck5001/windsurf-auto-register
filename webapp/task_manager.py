from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any

from windsurf_auth_replay import request_stop
from windsurf_auth_replay import summarize_result

from webapp.repository import Repository
from webapp.workflow_runner import WorkflowRequest, run_workflow_once


def _account_updates_from_result(result: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    email = str(result.get("email") or "").strip()
    ott = str(result.get("ott") or "").strip()
    session_token = str(result.get("session_token") or "").strip()
    trial_checkout_url = str(result.get("trial_checkout_url") or "").strip()
    pool_status = str(
        ((result.get("pool_result") or {}).get("account") or {}).get("status") or ""
    ).strip()
    if email:
        updates["email"] = email
    if ott:
        updates["ott"] = ott
    if session_token:
        updates["session_token"] = session_token
    if trial_checkout_url:
        updates["trial_checkout_url"] = trial_checkout_url
    if pool_status:
        updates["pool_status"] = pool_status
    return updates


@dataclass
class TaskManager:
    repo: Repository
    paused: bool = False
    current_task_id: int | None = None

    def __post_init__(self) -> None:
        self._event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            self._event.wait(timeout=1.0)
            self._event.clear()
            self.run_next_once()

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
            ott=payload.get("ott", ""),
            label=payload.get("label", ""),
            session_token=payload.get("session_token", ""),
        )
        try:
            result = run_workflow_once(request, on_event=on_event)
            self.repo.mark_succeeded(task_id, summarize_result(result, include_secrets=False))
            if payload.get("account_id"):
                updates = _account_updates_from_result(result)
                if updates:
                    self.repo.update_account(int(payload["account_id"]), updates)
            elif isinstance(result.get("accounts"), list):
                for account_result in result["accounts"]:
                    if isinstance(account_result, dict):
                        self.repo.save_account_result(task_id, account_result.get("mode", task["mode"]), account_result)
            else:
                self.repo.save_account_result(task_id, task["mode"], result)
        except Exception as exc:
            self.repo.mark_failed(task_id, str(exc))
        finally:
            self.current_task_id = None

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False
        self.wake()

    def wake(self) -> None:
        self._event.set()

    def stop(self, task_id: int) -> None:
        if self.current_task_id == task_id:
            request_stop()
        else:
            self.repo.cancel_queued_task(task_id)
