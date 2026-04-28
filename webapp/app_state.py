from __future__ import annotations

from pathlib import Path
import os
import time

from webapp.db import init_db
from webapp.env_loader import load_project_env
from webapp.repository import Repository
from webapp.runtime import load_runtime_settings
from webapp.task_manager import TaskManager
from windsurf_auth_replay import WindsurfPoolClient


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def configure_app_state(app) -> None:
    load_project_env()
    settings = load_runtime_settings()
    db_path = getattr(app.state, "db_path", settings.db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    app.state.asset_version = os.getenv("WINDSURF_ADMIN_ASSET_VERSION", str(int(time.time())))
    app.state.runtime_settings = settings
    app.state.db_path = db_path
    init_db(db_path)
    app.state.repository = Repository(db_path)
    app.state.repository.mark_stale_running_tasks_failed(
        "Worker restarted before task completed"
    )
    app.state.task_manager = TaskManager(app.state.repository)
    pool_base_url = os.getenv("WINDSURF_POOL_URL", "").strip()
    if pool_base_url:
        app.state.pool_client = WindsurfPoolClient(
            base_url=pool_base_url,
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
            verify_ssl=_env_bool("VERIFY_SSL", True),
            upload_mode=os.getenv("WINDSURF_POOL_UPLOAD_MODE", "auth"),
            dashboard_password=os.getenv("WINDSURF_POOL_DASHBOARD_PASSWORD", ""),
            ssh_key_path=os.getenv("WINDSURF_POOL_SSH_KEY_PATH", "~/.ssh/id_ed25519"),
            ssh_user=os.getenv("WINDSURF_POOL_SSH_USER", "root"),
        )
    else:
        app.state.pool_client = None
