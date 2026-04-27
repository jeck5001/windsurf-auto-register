from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from webapp.db import connect


class Repository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def create_task(self, mode: str, payload: dict[str, Any]) -> int:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "insert into tasks(mode, status, payload_json) values (?, 'queued', ?)",
                (mode, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def get_next_queued_task(self) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "select * from tasks where status = 'queued' order by id limit 1"
            ).fetchone()
            return dict(row) if row else None

    def mark_running(self, task_id: int) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "update tasks set status = 'running', started_at = current_timestamp where id = ?",
                (task_id,),
            )

    def mark_succeeded(self, task_id: int, result: dict[str, Any]) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "update tasks set status = 'succeeded', result_json = ?, finished_at = current_timestamp where id = ?",
                (json.dumps(result, ensure_ascii=False), task_id),
            )

    def mark_failed(self, task_id: int, error_text: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "update tasks set status = 'failed', error_text = ?, finished_at = current_timestamp where id = ?",
                (error_text, task_id),
            )

    def add_event(self, task_id: int, level: str, message: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "insert into task_events(task_id, level, message) values (?, ?, ?)",
                (task_id, level, message),
            )

    def list_task_events(self, task_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "select level, message, created_at from task_events where task_id = ? order by id desc limit ?",
                (task_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def request_stop(self, task_id: int) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "update tasks set stop_requested = 1 where id = ? and status in ('queued', 'running')",
                (task_id,),
            )

    def cancel_queued_task(self, task_id: int) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "update tasks set status = 'cancelled', finished_at = current_timestamp where id = ? and status = 'queued'",
                (task_id,),
            )

    def clone_task_for_retry(self, task_id: int) -> int:
        original = self.get_task(task_id)
        return self.create_task(mode=original["mode"], payload=original["payload"])

    def save_account_result(self, task_id: int, mode: str, result: dict[str, Any]) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                insert into accounts(task_id, email, mode, ott, trial_checkout_url, pool_status)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    result.get("email", ""),
                    mode,
                    result.get("ott", ""),
                    result.get("trial_checkout_url", ""),
                    ((result.get("pool_result") or {}).get("account") or {}).get("status", ""),
                ),
            )

    def list_accounts(self, limit: int = 50) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "select id, task_id, email, mode, ott, trial_checkout_url, pool_status, created_at from accounts order by id desc limit ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_task(self, task_id: int) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "select * from tasks where id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(task_id)
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        result["result"] = json.loads(result["result_json"]) if result.get("result_json") else None
        return result
