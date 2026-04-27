from __future__ import annotations

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
