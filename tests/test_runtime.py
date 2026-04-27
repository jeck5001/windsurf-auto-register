from pathlib import Path

import pytest

from webapp.runtime import RuntimeSettings, load_runtime_settings
from webapp.workflow_runner import WorkflowRequest, validate_runtime_support
from windsurf_auth_replay import WorkflowError


def test_load_runtime_settings_prefers_docker_db_path(monkeypatch):
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    monkeypatch.setenv("WINDSURF_ADMIN_DB_PATH", "/app/data/windsurf_admin.db")

    settings = load_runtime_settings()

    assert settings.docker_mode is True
    assert settings.db_path == Path("/app/data/windsurf_admin.db")
    assert settings.browser_automation_supported is False


def test_validate_runtime_support_rejects_browser_flows_in_docker():
    settings = RuntimeSettings(
        db_path=Path("/app/data/windsurf_admin.db"),
        docker_mode=True,
        browser_automation_supported=False,
    )

    with pytest.raises(
        WorkflowError,
        match="Docker runtime does not support browser automation flows in v1",
    ):
        validate_runtime_support(
            WorkflowRequest(
                mode="trial-browser",
                email="",
                password="",
                account_count=1,
                generate_trial_link=False,
            ),
            settings,
        )


def test_docker_assets_exist():
    assert Path("Dockerfile").exists()
    assert Path("docker-compose.yml").exists()
    assert Path(".dockerignore").exists()
