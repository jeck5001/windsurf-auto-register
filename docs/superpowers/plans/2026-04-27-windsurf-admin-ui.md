# Windsurf Admin UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a browser-based admin console for `windsurf-auto-register` that can launch runs, monitor queue and logs, inspect produced accounts, and manage configuration state without replacing the existing automation core.

**Architecture:** Keep the repo Python-first. Add a small FastAPI app that serves server-rendered multi-page admin screens plus JSON/SSE endpoints. Wrap the existing CLI workflows in a programmatic task runner, persist task state in SQLite, and use one in-process worker thread for queued jobs so the first version stays simple and testable.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Jinja2 templates, vanilla JavaScript, SQLite (`sqlite3`), pytest, httpx

---

## File Map

### Existing Files To Modify

- Modify: `requirements.txt`
  Runtime dependencies for the web management layer.
- Modify: `windsurf_auth_replay.py`
  Add workflow event hooks, cooperative stop checkpoints, and a programmatic argument adapter that the web layer can call without invoking the CLI parser.

### New Runtime Files

- Create: `requirements-dev.txt`
  Test-only dependencies.
- Create: `webapp/__init__.py`
  Package marker.
- Create: `webapp/app.py`
  FastAPI app entrypoint, router registration, and startup hooks.
- Create: `webapp/db.py`
  SQLite schema creation and connection helpers.
- Create: `webapp/repository.py`
  CRUD operations for tasks, task events, accounts, and settings snapshots.
- Create: `webapp/task_manager.py`
  Single-worker queue manager, background run orchestration, pause/resume/stop handling.
- Create: `webapp/workflow_runner.py`
  Adapter from structured web requests to the existing Windsurf workflows.
- Create: `webapp/config_health.py`
  Safe environment inspection and configuration validation summaries.
- Create: `webapp/routes_pages.py`
  HTML page routes for `Dashboard`, `Tasks`, `Accounts`, and `Settings`.
- Create: `webapp/routes_api.py`
  JSON APIs for task creation, task controls, task detail, and account/settings data.
- Create: `webapp/templates/base.html`
  Shared admin shell and navigation.
- Create: `webapp/templates/dashboard.html`
  Dashboard command-center view.
- Create: `webapp/templates/tasks.html`
  Task builder and run table.
- Create: `webapp/templates/accounts.html`
  Output/account history screen.
- Create: `webapp/templates/settings.html`
  Provider/API/runtime settings summary screen.
- Create: `webapp/static/admin.css`
  Low-glare light theme and page layout.
- Create: `webapp/static/admin.js`
  Task form submission, polling, row selection, and live log EventSource handling.

### New Test Files

- Create: `tests/test_app_boot.py`
  App import and health checks.
- Create: `tests/test_workflow_runner.py`
  Programmatic workflow adapter behavior and event emission.
- Create: `tests/test_task_manager.py`
  Queue behavior, pause/resume, cooperative stop, and persistence updates.
- Create: `tests/test_pages.py`
  Page route rendering and navigation smoke tests.
- Create: `tests/test_task_api.py`
  API behavior for task creation, control actions, and event streaming.
- Create: `tests/test_config_health.py`
  Settings/health summarization behavior.

## Implementation Notes

- Stay Python-only for the first version. Do not add Node, React, or a build pipeline.
- Use server-rendered pages plus small vanilla JS for interactivity.
- Use SQLite in the repo root by default, for example `windsurf_admin.db`.
- Queue semantics for v1:
  - `Pause`: stop dequeuing new tasks.
  - `Resume`: allow dequeuing again.
  - `Stop`: cooperative cancellation for the running task at explicit checkpoints plus immediate cancellation for queued tasks.
- Live logs should use `text/event-stream` so the dashboard and task detail pane can update without page refresh.
- Keep secrets masked in the UI. Settings pages should report presence and health, not raw secret values.

### Task 1: Bootstrap the web app shell

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `webapp/__init__.py`
- Create: `webapp/app.py`
- Create: `tests/test_app_boot.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from webapp.app import app


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_root_redirects_to_dashboard():
    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_boot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webapp'`

- [ ] **Step 3: Write minimal implementation**

`requirements.txt`
```text
requests
patchright
fastapi
uvicorn
jinja2
python-multipart
```

`requirements-dev.txt`
```text
pytest
httpx
```

`webapp/app.py`
```python
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(title="Windsurf Admin")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app_boot.py -v`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt requirements-dev.txt webapp/__init__.py webapp/app.py tests/test_app_boot.py
git commit -m "feat: bootstrap fastapi admin shell"
```

### Task 2: Add workflow hooks and a programmatic runner

**Files:**
- Modify: `windsurf_auth_replay.py`
- Create: `webapp/workflow_runner.py`
- Create: `tests/test_workflow_runner.py`

- [ ] **Step 1: Write the failing test**

```python
from types import SimpleNamespace

from webapp.workflow_runner import WorkflowRequest, run_workflow_once


def test_run_workflow_once_emits_masked_events(monkeypatch):
    events: list[dict[str, str]] = []

    def fake_full_workflow(config, args):
        return {"mode": "full", "email": "demo@example.com", "ott": "ott$secret-token"}

    monkeypatch.setattr("webapp.workflow_runner.full_workflow", fake_full_workflow)
    monkeypatch.setattr("webapp.workflow_runner.build_config", lambda args: SimpleNamespace())

    result = run_workflow_once(
        WorkflowRequest(mode="full", email="", password="", account_count=1, generate_trial_link=False),
        on_event=events.append,
    )

    assert result["mode"] == "full"
    assert result["ott"].startswith("ott$")
    assert any(event["level"] == "info" for event in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workflow_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webapp.workflow_runner'`

- [ ] **Step 3: Write minimal implementation**

`windsurf_auth_replay.py`
```python
from contextvars import ContextVar

_event_callback: ContextVar[Optional[callable]] = ContextVar("_event_callback", default=None)
_stop_requested: ContextVar[bool] = ContextVar("_stop_requested", default=False)


def set_event_callback(callback):
    return _event_callback.set(callback)


def reset_event_callback(token) -> None:
    _event_callback.reset(token)


def request_stop() -> None:
    _stop_requested.set(True)


def clear_stop_request() -> None:
    _stop_requested.set(False)


def workflow_checkpoint(label: str) -> None:
    callback = _event_callback.get()
    if callback:
        callback({"level": "debug", "message": label})
    if _stop_requested.get():
        raise WorkflowError("任务被用户停止")


def _emit_event(level: str, message: str) -> None:
    callback = _event_callback.get()
    if callback:
        callback({"level": level, "message": message})


def print_step(message: str) -> None:
    _emit_event("info", message)
    print(f"[*] {message}")


def print_success(message: str) -> None:
    _emit_event("success", message)
    print(f"[+] {message}")


def print_warn(message: str) -> None:
    _emit_event("warning", message)
    print(f"[!] {message}")
```

`webapp/workflow_runner.py`
```python
from argparse import Namespace
from dataclasses import dataclass
from typing import Any, Callable

from windsurf_auth_replay import (
    WorkflowError,
    build_config,
    clear_stop_request,
    full_workflow,
    reset_event_callback,
    set_event_callback,
    summarize_result,
    trial_browser_workflow,
    trial_workflow,
    upload_only_workflow,
)


@dataclass
class WorkflowRequest:
    mode: str
    email: str
    password: str
    account_count: int
    generate_trial_link: bool


def _build_args(request: WorkflowRequest) -> Namespace:
    return Namespace(
        mode=request.mode,
        email=request.email,
        name="",
        password=request.password,
        label="",
        ott="",
        session_token="",
        account_count=request.account_count,
        base_url="https://windsurf.com",
        pool_base_url="",
        pool_upload_mode="auth",
        pool_dashboard_password="",
        pool_ssh_key_path="~/.ssh/id_ed25519",
        pool_ssh_user="root",
        yyds_base_url="https://maliapi.215.im/v1",
        yyds_api_key="",
        yyds_domain="",
        yyds_subdomain="",
        yyds_local_part="",
        request_timeout=20,
        poll_timeout=60,
        poll_interval=5,
        max_attempts=5,
        insecure=False,
        debug=False,
        generate_trial_link=request.generate_trial_link,
        turnstile_token="",
        turnstile_site_url="",
        turnstile_sitekey="",
        turnstile_solver_url="",
        turnstile_browser_path="",
        turnstile_timeout=90,
        headed_turnstile=False,
        login_url="",
        billing_url="",
        headless_browser=False,
        trial_success_url="",
        trial_cancel_url="",
        trial_plan_id="",
        output_json="",
        include_secrets_in_output=False,
        show_secrets=False,
    )


def run_workflow_once(
    request: WorkflowRequest,
    on_event: Callable[[dict[str, str]], None],
) -> dict[str, Any]:
    args = _build_args(request)
    config = build_config(args)
    token = set_event_callback(on_event)
    clear_stop_request()
    try:
        on_event({"level": "info", "message": f"starting mode={request.mode}"})
        if request.mode == "upload":
            result = upload_only_workflow(config, args)
        elif request.mode == "trial":
            result = trial_workflow(config, args)
        elif request.mode == "trial-browser":
            result = trial_browser_workflow(config, args)
        else:
            result = full_workflow(config, args)
        return summarize_result(result, include_secrets=False)
    except WorkflowError as exc:
        on_event({"level": "error", "message": str(exc)})
        raise
    finally:
        reset_event_callback(token)
        clear_stop_request()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workflow_runner.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add windsurf_auth_replay.py webapp/workflow_runner.py tests/test_workflow_runner.py
git commit -m "feat: add workflow runner for web tasks"
```

### Task 3: Add SQLite persistence and the in-process task manager

**Files:**
- Create: `webapp/db.py`
- Create: `webapp/repository.py`
- Create: `webapp/task_manager.py`
- Modify: `windsurf_auth_replay.py`
- Create: `tests/test_task_manager.py`

- [ ] **Step 1: Write the failing test**

```python
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
        lambda request, on_event: {"mode": request.mode, "email": "done@example.com", "ott": "ott$masked"},
    )

    task_id = repo.create_task(mode="full", payload={"account_count": 1})
    manager.run_next_once()
    task = repo.get_task(task_id)

    assert task["status"] == "succeeded"
    assert task["result"]["email"] == "done@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_manager.py -v`
Expected: FAIL with `ModuleNotFoundError` for `webapp.db` or `webapp.repository`

- [ ] **Step 3: Write minimal implementation**

`webapp/db.py`
```python
from pathlib import Path
import sqlite3


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path) -> None:
    connection = connect(db_path)
    connection.executescript(
        """
        create table if not exists tasks (
            id integer primary key autoincrement,
            mode text not null,
            status text not null,
            payload_json text not null,
            result_json text,
            error_text text,
            stop_requested integer not null default 0,
            created_at text not null default current_timestamp,
            started_at text,
            finished_at text
        );

        create table if not exists task_events (
            id integer primary key autoincrement,
            task_id integer not null,
            level text not null,
            message text not null,
            created_at text not null default current_timestamp
        );

        create table if not exists accounts (
            id integer primary key autoincrement,
            task_id integer not null,
            email text,
            mode text not null,
            ott text,
            trial_checkout_url text,
            pool_status text,
            created_at text not null default current_timestamp
        );
        """
    )
    connection.commit()
    connection.close()
```

`webapp/repository.py`
```python
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

    def get_task(self, task_id: int) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            row = connection.execute("select * from tasks where id = ?", (task_id,)).fetchone()
            result = dict(row)
            result["payload"] = json.loads(result.pop("payload_json"))
            result["result"] = json.loads(result["result_json"]) if result.get("result_json") else None
            return result
```

`webapp/task_manager.py`
```python
from dataclasses import dataclass
from typing import Any

from webapp.repository import Repository
from webapp.workflow_runner import WorkflowRequest, run_workflow_once


@dataclass
class TaskManager:
    repo: Repository
    paused: bool = False

    def run_next_once(self) -> None:
        if self.paused:
            return
        task = self.repo.get_next_queued_task()
        if not task:
            return
        task_id = int(task["id"])
        self.current_task_id = task_id
        payload: dict[str, Any] = __import__("json").loads(task["payload_json"])
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
```

`windsurf_auth_replay.py`
```python
def request_verification_code(self, email: str) -> str:
    workflow_checkpoint("request_verification_code")
    response = self.session.post(
        f"{self.base_url}/_devin-auth/email/start",
        headers=self._json_headers(),
        json={"email": email, "mode": "signup", "product": "Windsurf"},
        timeout=self.request_timeout,
        verify=self.verify_ssl,
    )
    raise_for_http(response, "发送验证码")
    payload = maybe_json(response)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise WorkflowError(f"发送验证码失败: {payload}")
    token = payload.get("email_verification_token")
    if not token:
        raise WorkflowError("发送验证码失败: 没有拿到 email_verification_token")
    return token
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_manager.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add webapp/db.py webapp/repository.py webapp/task_manager.py windsurf_auth_replay.py tests/test_task_manager.py
git commit -m "feat: add task persistence and worker manager"
```

### Task 4: Build the shared admin shell and theme

**Files:**
- Modify: `webapp/app.py`
- Create: `webapp/routes_pages.py`
- Create: `webapp/templates/base.html`
- Create: `webapp/templates/dashboard.html`
- Create: `webapp/templates/tasks.html`
- Create: `webapp/templates/accounts.html`
- Create: `webapp/templates/settings.html`
- Create: `webapp/static/admin.css`
- Create: `tests/test_pages.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from webapp.app import app


def test_dashboard_page_renders_navigation():
    client = TestClient(app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Tasks" in response.text
    assert "Accounts" in response.text
    assert "Settings" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pages.py::test_dashboard_page_renders_navigation -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Write minimal implementation**

`webapp/app.py`
```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from webapp.db import init_db
from webapp.repository import Repository
from webapp.routes_pages import router as pages_router
from webapp.task_manager import TaskManager

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Windsurf Admin")
app.include_router(pages_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    app.state.db_path = getattr(app.state, "db_path", Path("windsurf_admin.db"))
    init_db(app.state.db_path)
    app.state.repository = Repository(app.state.db_path)
    app.state.task_manager = TaskManager(app.state.repository)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)
```

`webapp/routes_pages.py`
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="webapp/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"page": "dashboard", "title": "Dashboard", "stats": [], "tasks": [], "events": []},
    )


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    return templates.TemplateResponse(request, "tasks.html", {"page": "tasks", "title": "Tasks", "tasks": []})


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request):
    return templates.TemplateResponse(request, "accounts.html", {"page": "accounts", "title": "Accounts", "accounts": []})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"page": "settings", "title": "Settings", "checks": []})
```

`webapp/templates/base.html`
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} · Windsurf Admin</title>
    <link rel="stylesheet" href="/static/admin.css">
  </head>
  <body>
    <div class="shell">
      <aside class="rail">
        <div class="brand">WA</div>
        <a href="/dashboard" class="{% if page == 'dashboard' %}active{% endif %}">Dashboard</a>
        <a href="/tasks" class="{% if page == 'tasks' %}active{% endif %}">Tasks</a>
        <a href="/accounts" class="{% if page == 'accounts' %}active{% endif %}">Accounts</a>
        <a href="/settings" class="{% if page == 'settings' %}active{% endif %}">Settings</a>
      </aside>
      <main class="content">
        {% block content %}{% endblock %}
      </main>
    </div>
    <script src="/static/admin.js"></script>
  </body>
  </html>
```

`webapp/templates/dashboard.html`
```html
{% extends "base.html" %}
{% block content %}
<header class="page-header">
  <h1>Dashboard</h1>
  <p>Command center for current runs, queue health, and live logs.</p>
</header>
{% endblock %}
```

`webapp/static/admin.css`
```css
:root {
  --bg: #f3f5f6;
  --panel: rgba(255, 255, 255, 0.82);
  --text: #182028;
  --muted: #5b6772;
  --line: #dbe2e7;
  --accent: #1f252b;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 88px 1fr;
}
.rail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px 12px;
  background: rgba(247, 249, 250, 0.92);
  border-right: 1px solid var(--line);
}
.rail a {
  color: var(--muted);
  text-decoration: none;
  padding: 10px 12px;
  border-radius: 12px;
}
.rail a.active {
  color: var(--text);
  background: #dde4e9;
}
.content {
  padding: 24px;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pages.py::test_dashboard_page_renders_navigation -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py webapp/routes_pages.py webapp/templates webapp/static/admin.css webapp/static/admin.js tests/test_pages.py
git commit -m "feat: add admin page shell and theme"
```

### Task 5: Implement the Dashboard command center

**Files:**
- Modify: `webapp/repository.py`
- Modify: `webapp/routes_pages.py`
- Modify: `webapp/templates/dashboard.html`
- Modify: `webapp/static/admin.css`
- Modify: `webapp/static/admin.js`
- Create: `tests/test_pages.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from webapp.app import app


def test_dashboard_shows_stats_from_repository(tmp_path):
    app.state.db_path = tmp_path / "admin.db"
    from webapp.db import init_db
    from webapp.repository import Repository

    init_db(app.state.db_path)
    repo = Repository(app.state.db_path)
    repo.create_task(mode="full", payload={"account_count": 1})

    client = TestClient(app)
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Queued Tasks" in response.text
    assert "Recent Events" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pages.py::test_dashboard_shows_stats_from_repository -v`
Expected: FAIL because the page does not include the dashboard panels yet

- [ ] **Step 3: Write minimal implementation**

`webapp/repository.py`
```python
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
```

`webapp/routes_pages.py`
```python
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    snapshot = request.app.state.repository.dashboard_snapshot()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page": "dashboard",
            "title": "Dashboard",
            "stats": snapshot["stats"],
            "tasks": snapshot["tasks"],
            "events": snapshot["events"],
        },
    )
```

`webapp/templates/dashboard.html`
```html
{% extends "base.html" %}
{% block content %}
<header class="page-header">
  <h1>Dashboard</h1>
  <p>Command center for current runs, queue health, and live logs.</p>
</header>

<section class="stats-grid">
  <article class="panel"><span>Running</span><strong>{{ stats.running }}</strong></article>
  <article class="panel"><span>Queued Tasks</span><strong>{{ stats.queued }}</strong></article>
  <article class="panel"><span>Failed</span><strong>{{ stats.failed }}</strong></article>
  <article class="panel"><span>Succeeded</span><strong>{{ stats.succeeded }}</strong></article>
</section>

<section class="board-grid">
  <article class="panel">
    <h2>Active and Recent Tasks</h2>
    <table>
      <thead><tr><th>ID</th><th>Mode</th><th>Status</th></tr></thead>
      <tbody>
        {% for task in tasks %}
        <tr><td>#{{ task.id }}</td><td>{{ task.mode }}</td><td>{{ task.status }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </article>
  <article class="panel panel-dark">
    <h2>Recent Events</h2>
    <ul class="event-list">
      {% for event in events %}
      <li><span>{{ event.level }}</span><p>{{ event.message }}</p></li>
      {% endfor %}
    </ul>
  </article>
</section>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pages.py::test_dashboard_shows_stats_from_repository -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add webapp/repository.py webapp/routes_pages.py webapp/templates/dashboard.html webapp/static/admin.css webapp/static/admin.js tests/test_pages.py
git commit -m "feat: implement dashboard command center"
```

### Task 6: Implement task creation, controls, and live logs

**Files:**
- Modify: `webapp/task_manager.py`
- Create: `webapp/routes_api.py`
- Modify: `webapp/app.py`
- Modify: `webapp/routes_pages.py`
- Modify: `webapp/templates/tasks.html`
- Modify: `webapp/static/admin.js`
- Create: `tests/test_task_api.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from webapp.app import app


def test_create_task_api_enqueues_full_run(tmp_path):
    app.state.db_path = tmp_path / "admin.db"
    from webapp.db import init_db

    init_db(app.state.db_path)
    client = TestClient(app)
    response = client.post(
        "/api/tasks",
        json={"mode": "full", "email": "", "password": "", "account_count": 2, "generate_trial_link": False},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_retry_and_stop_endpoints_return_control_states(tmp_path):
    app.state.db_path = tmp_path / "admin.db"
    from webapp.db import init_db
    from webapp.repository import Repository

    init_db(app.state.db_path)
    repo = Repository(app.state.db_path)
    task_id = repo.create_task(mode="full", payload={"account_count": 1})

    client = TestClient(app)
    stop_response = client.post(f"/api/tasks/{task_id}/stop")
    retry_response = client.post(f"/api/tasks/{task_id}/retry")

    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stop_requested"
    assert retry_response.status_code == 201
    assert retry_response.json()["status"] == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_api.py::test_create_task_api_enqueues_full_run -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Write minimal implementation**

`webapp/routes_api.py`
```python
from fastapi import APIRouter, Request, status

from windsurf_auth_replay import request_stop

router = APIRouter(prefix="/api")


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(request: Request, payload: dict):
    repo = request.app.state.repository
    task_id = repo.create_task(mode=payload["mode"], payload=payload)
    request.app.state.task_manager.wake()
    task = repo.get_task(task_id)
    return {"id": task_id, "status": task["status"], "payload": task["payload"]}


@router.post("/queue/pause")
async def pause_queue(request: Request):
    request.app.state.task_manager.pause()
    return {"ok": True, "paused": True}


@router.post("/queue/resume")
async def resume_queue(request: Request):
    request.app.state.task_manager.resume()
    return {"ok": True, "paused": False}


@router.post("/tasks/{task_id}/stop")
async def stop_task(request: Request, task_id: int):
    request.app.state.repository.request_stop(task_id)
    request.app.state.task_manager.stop(task_id)
    return {"ok": True, "task_id": task_id, "status": "stop_requested"}


@router.post("/tasks/{task_id}/retry", status_code=status.HTTP_201_CREATED)
async def retry_task(request: Request, task_id: int):
    new_task_id = request.app.state.repository.clone_task_for_retry(task_id)
    request.app.state.task_manager.wake()
    return {"ok": True, "task_id": new_task_id, "status": "queued"}
```

`webapp/task_manager.py`
```python
import threading
import time

from windsurf_auth_replay import request_stop


class TaskManager:
    def __init__(self, repo):
        self.repo = repo
        self.paused = False
        self._event = threading.Event()
        self.current_task_id = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            self._event.wait(timeout=1.0)
            self._event.clear()
            self.run_next_once()

    def wake(self) -> None:
        self._event.set()

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False
        self.wake()

    def stop(self, task_id: int) -> None:
        if self.current_task_id == task_id:
            request_stop()
        else:
            self.repo.cancel_queued_task(task_id)
```

`webapp/templates/tasks.html`
```html
{% extends "base.html" %}
{% block content %}
<header class="page-header">
  <h1>Tasks</h1>
  <p>Create runs, control queue execution, and inspect per-task results.</p>
</header>

<section class="task-layout">
  <form id="task-form" class="panel">
    <label>Mode
      <select name="mode">
        <option value="full">full</option>
        <option value="trial">trial</option>
        <option value="trial-browser">trial-browser</option>
        <option value="upload">upload</option>
      </select>
    </label>
    <label>Account Count <input type="number" name="account_count" value="1" min="1"></label>
    <label>Email <input type="email" name="email"></label>
    <label>Password <input type="password" name="password"></label>
    <label><input type="checkbox" name="generate_trial_link"> Generate trial link</label>
    <button type="submit">Create Task</button>
  </form>
  <section class="panel">
    <h2>Recent Tasks</h2>
    <div id="task-table"></div>
  </section>
</section>
{% endblock %}
```

`webapp/static/admin.js`
```javascript
async function submitTaskForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  data.account_count = Number(data.account_count || "1");
  data.generate_trial_link = form.querySelector("[name=generate_trial_link]").checked;
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    alert("Failed to create task");
    return;
  }
  window.location.reload();
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("task-form");
  if (form) {
    form.addEventListener("submit", submitTaskForm);
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_api.py::test_create_task_api_enqueues_full_run -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add webapp/task_manager.py webapp/routes_api.py webapp/app.py webapp/routes_pages.py webapp/templates/tasks.html webapp/static/admin.js tests/test_task_api.py
git commit -m "feat: add task creation and queue controls"
```

### Task 7: Add accounts history and settings health views

**Files:**
- Create: `webapp/config_health.py`
- Modify: `webapp/repository.py`
- Modify: `webapp/routes_pages.py`
- Modify: `webapp/templates/accounts.html`
- Modify: `webapp/templates/settings.html`
- Create: `tests/test_config_health.py`
- Modify: `tests/test_pages.py`

- [ ] **Step 1: Write the failing test**

```python
from webapp.config_health import build_health_snapshot


def test_build_health_snapshot_masks_secret_values(monkeypatch):
    monkeypatch.setenv("YYDS_MAIL_API_KEY", "secret-key")
    snapshot = build_health_snapshot()

    assert snapshot["checks"]["yyds_api_key"]["present"] is True
    assert snapshot["checks"]["yyds_api_key"]["display"] == "configured"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webapp.config_health'`

- [ ] **Step 3: Write minimal implementation**

`webapp/config_health.py`
```python
import os


def build_health_snapshot() -> dict:
    checks = {
        "yyds_api_key": {"present": bool(os.getenv("YYDS_MAIL_API_KEY")), "display": "configured" if os.getenv("YYDS_MAIL_API_KEY") else "missing"},
        "pool_url": {"present": bool(os.getenv("WINDSURF_POOL_URL")), "display": "configured" if os.getenv("WINDSURF_POOL_URL") else "missing"},
        "turnstile_mode": {"present": True, "display": "browser or token"},
    }
    overall_ok = all(item["present"] for key, item in checks.items() if key != "turnstile_mode")
    return {"ok": overall_ok, "checks": checks}
```

`webapp/repository.py`
```python
    def list_accounts(self, limit: int = 50) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "select id, task_id, email, mode, ott, trial_checkout_url, pool_status, created_at from accounts order by id desc limit ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
```

`webapp/routes_pages.py`
```python
from webapp.config_health import build_health_snapshot


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request):
    accounts = request.app.state.repository.list_accounts()
    return templates.TemplateResponse(
        request,
        "accounts.html",
        {"page": "accounts", "title": "Accounts", "accounts": accounts},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    snapshot = build_health_snapshot()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"page": "settings", "title": "Settings", "checks": snapshot["checks"], "settings_ok": snapshot["ok"]},
    )
```

`webapp/templates/accounts.html`
```html
{% extends "base.html" %}
{% block content %}
<header class="page-header">
  <h1>Accounts</h1>
  <p>Review produced accounts, OTT upload state, and trial link outputs.</p>
</header>
<section class="panel">
  <table>
    <thead><tr><th>Email</th><th>Mode</th><th>Pool Status</th><th>Trial URL</th></tr></thead>
    <tbody>
      {% for account in accounts %}
      <tr>
        <td>{{ account.email }}</td>
        <td>{{ account.mode }}</td>
        <td>{{ account.pool_status }}</td>
        <td>{{ "yes" if account.trial_checkout_url else "no" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
```

`webapp/templates/settings.html`
```html
{% extends "base.html" %}
{% block content %}
<header class="page-header">
  <h1>Settings</h1>
  <p>Environment readiness for YYDS Mail, Pool API, and trial generation.</p>
</header>
<section class="settings-grid">
  {% for name, item in checks.items() %}
  <article class="panel">
    <h2>{{ name }}</h2>
    <strong>{{ item.display }}</strong>
  </article>
  {% endfor %}
</section>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_health.py tests/test_pages.py -v`
Expected: PASS with all new settings/accounts assertions passing

- [ ] **Step 5: Commit**

```bash
git add webapp/config_health.py webapp/repository.py webapp/routes_pages.py webapp/templates/accounts.html webapp/templates/settings.html tests/test_config_health.py tests/test_pages.py
git commit -m "feat: add accounts history and settings health views"
```

### Task 8: Add live event streaming, app state wiring, and launch docs

**Files:**
- Create: `webapp/app_state.py`
- Modify: `webapp/app.py`
- Modify: `webapp/routes_api.py`
- Modify: `webapp/static/admin.js`
- Modify: `README.md`
- Modify: `tests/test_task_api.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from webapp.app import app


def test_task_events_endpoint_returns_sse(tmp_path):
    app.state.db_path = tmp_path / "admin.db"
    from webapp.db import init_db
    from webapp.repository import Repository

    init_db(app.state.db_path)
    repo = Repository(app.state.db_path)
    task_id = repo.create_task(mode="full", payload={"account_count": 1})
    repo.add_event(task_id, "info", "task created")

    client = TestClient(app)
    response = client.get(f"/api/tasks/{task_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "task created" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_api.py::test_task_events_endpoint_returns_sse -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Write minimal implementation**

`webapp/app_state.py`
```python
from pathlib import Path

from webapp.db import init_db
from webapp.repository import Repository
from webapp.task_manager import TaskManager


def configure_app_state(app) -> None:
    db_path = getattr(app.state, "db_path", Path("windsurf_admin.db"))
    app.state.db_path = db_path
    init_db(db_path)
    app.state.repository = Repository(db_path)
    app.state.task_manager = TaskManager(app.state.repository)


def get_repository(app):
    return app.state.repository


def get_task_manager(app):
    return app.state.task_manager
```

`webapp/app.py`
```python
from contextlib import asynccontextmanager

from webapp.app_state import configure_app_state


@asynccontextmanager
async def lifespan(app):
    configure_app_state(app)
    yield


app = FastAPI(title="Windsurf Admin", lifespan=lifespan)
app.include_router(pages_router)
app.include_router(api_router)
```

`webapp/routes_api.py`
```python
import json
from fastapi.responses import StreamingResponse


@router.get("/tasks/{task_id}/events")
async def task_events(request: Request, task_id: int):
    repo = request.app.state.repository
    events = repo.list_task_events(task_id, limit=100)

    def event_stream():
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

`webapp/static/admin.js`
```javascript
function attachTaskEventStream(taskId, target) {
  const source = new EventSource(`/api/tasks/${taskId}/events`);
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    const item = document.createElement("li");
    item.textContent = `${payload.level}: ${payload.message}`;
    target.prepend(item);
  };
}
```

`README.md`
```markdown
## Web Admin

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the admin server:

```bash
uvicorn webapp.app:app --reload
```

Open [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_api.py -v`
Expected: PASS with SSE and task API assertions passing

- [ ] **Step 5: Commit**

```bash
git add webapp/app_state.py webapp/app.py webapp/routes_api.py webapp/static/admin.js README.md tests/test_task_api.py
git commit -m "feat: wire live events and admin startup docs"
```

## Self-Review Checklist

### Spec coverage

- Dashboard command center: covered by Tasks 4 and 5.
- Tasks primary operating surface: covered by Task 6.
- Accounts history page: covered by Task 7.
- Settings readiness page: covered by Task 7.
- Low-glare multi-page admin shell: covered by Task 4.
- Live logs and runtime monitoring: covered by Tasks 2, 3, 5, and 8.
- Python-first incremental architecture: covered by Tasks 1, 2, and 3.

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” markers remain.
- Each task includes concrete file paths, code snippets, and commands.

### Type consistency

- Shared `WorkflowRequest` fields stay consistent across the runner and task manager.
- Repository methods used by pages and APIs are defined in the repository layer.
- App state access is centralized in `webapp.app_state`.
