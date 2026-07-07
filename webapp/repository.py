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

    def mark_stale_running_tasks_failed(self, error_text: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                update tasks
                set status = 'failed', error_text = ?, finished_at = current_timestamp
                where status = 'running'
                """,
                (error_text,),
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
                insert into accounts(task_id, email, password, mode, ott, session_token, trial_checkout_url, pool_status)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    result.get("email", ""),
                    result.get("password", ""),
                    mode,
                    result.get("ott", ""),
                    result.get("session_token", ""),
                    result.get("trial_checkout_url", ""),
                    ((result.get("pool_result") or {}).get("account") or {}).get("status", ""),
                ),
            )

    def upsert_pool_account(self, email: str, pool_status: str, password: str = "") -> None:
        with connect(self.db_path) as connection:
            tombstone = connection.execute(
                "select email from account_tombstones where email = ?",
                (email,),
            ).fetchone()
            if tombstone is not None:
                return
            existing = connection.execute(
                "select id from accounts where email = ? order by id desc limit 1",
                (email,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    insert into accounts(task_id, email, password, mode, ott, session_token, trial_checkout_url, pool_status)
                    values (0, ?, ?, 'pool-sync', '', '', '', ?)
                    """,
                    (email, password, pool_status),
                )
            else:
                connection.execute(
                    """
                    update accounts
                    set
                        pool_status = coalesce(?, pool_status),
                        password = coalesce(nullif(?, ''), password)
                    where id = ?
                    """,
                    (pool_status or None, password, existing["id"]),
                )

    def list_accounts(self, limit: int | None = 50, offset: int = 0) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            sql = "select id, task_id, email, password, mode, ott, session_token, trial_checkout_url, pool_status, created_at from accounts order by id desc"
            if limit is None:
                rows = connection.execute(sql).fetchall()
            else:
                rows = connection.execute(f"{sql} limit ? offset ?", (limit, offset)).fetchall()
        return [dict(row) for row in rows]

    def count_accounts(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute("select count(*) as count from accounts").fetchone()
        return int(row["count"])

    def get_account(self, account_id: int) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "select id, task_id, email, password, mode, ott, session_token, trial_checkout_url, pool_status, created_at from accounts where id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise KeyError(account_id)
        return dict(row)

    def update_account(self, account_id: int, values: dict[str, Any]) -> dict[str, Any]:
        allowed_fields = ("email", "password", "pool_status", "trial_checkout_url", "ott", "session_token")
        updates = {
            key: str(values[key] or "")
            for key in allowed_fields
            if key in values
        }
        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            params = [*updates.values(), account_id]
            with connect(self.db_path) as connection:
                cursor = connection.execute(
                    f"update accounts set {assignments} where id = ?",
                    params,
                )
                if cursor.rowcount == 0:
                    raise KeyError(account_id)
        return self.get_account(account_id)

    def delete_account(self, account_id: int) -> None:
        with connect(self.db_path) as connection:
            existing = connection.execute(
                "select email from accounts where id = ?",
                (account_id,),
            ).fetchone()
            if existing is None:
                raise KeyError(account_id)
            email = str(existing["email"] or "").strip()
            if email:
                connection.execute(
                    "insert or replace into account_tombstones(email, deleted_at) values (?, current_timestamp)",
                    (email,),
                )
            cursor = connection.execute(
                "delete from accounts where id = ?",
                (account_id,),
            )
            if cursor.rowcount == 0:
                raise KeyError(account_id)

    def dashboard_snapshot(self) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            counts = connection.execute(
                """
                select
                    sum(case when status = 'running' then 1 else 0 end) as running_count,
                    sum(case when status = 'queued' then 1 else 0 end) as queued_count,
                    sum(case when status = 'failed' then 1 else 0 end) as failed_count,
                    sum(case when status = 'succeeded' then 1 else 0 end) as succeeded_count
                from tasks
                """
            ).fetchone()
            events = connection.execute(
                "select task_id, level, message, created_at from task_events order by id desc limit 20"
            ).fetchall()
            tasks = connection.execute(
                "select id, mode, status, created_at from tasks order by id desc limit 10"
            ).fetchall()
        return {
            "stats": {
                "running": int(counts["running_count"] or 0),
                "queued": int(counts["queued_count"] or 0),
                "failed": int(counts["failed_count"] or 0),
                "succeeded": int(counts["succeeded_count"] or 0),
            },
            "events": [dict(row) for row in events],
            "tasks": [dict(row) for row in tasks],
        }

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
