from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeSettings:
    db_path: Path
    docker_mode: bool
    browser_automation_supported: bool


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_runtime_settings() -> RuntimeSettings:
    docker_mode = _env_bool("RUNNING_IN_DOCKER", False)
    default_db_path = "/app/data/windsurf_admin.db" if docker_mode else "windsurf_admin.db"
    db_path = Path(os.getenv("WINDSURF_ADMIN_DB_PATH", default_db_path))
    return RuntimeSettings(
        db_path=db_path,
        docker_mode=docker_mode,
        browser_automation_supported=not docker_mode,
    )
