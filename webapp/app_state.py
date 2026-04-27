from __future__ import annotations

from pathlib import Path

from webapp.db import init_db
from webapp.repository import Repository
from webapp.runtime import load_runtime_settings
from webapp.task_manager import TaskManager


def configure_app_state(app) -> None:
    settings = load_runtime_settings()
    db_path = getattr(app.state, "db_path", settings.db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    app.state.runtime_settings = settings
    app.state.db_path = db_path
    init_db(db_path)
    app.state.repository = Repository(db_path)
    app.state.task_manager = TaskManager(app.state.repository)
