from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from webapp.config_health import build_health_snapshot

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    repo = getattr(request.app.state, "repository", None)
    snapshot = (
        repo.dashboard_snapshot()
        if repo is not None
        else {"stats": {"running": 0, "queued": 0, "failed": 0, "succeeded": 0}, "tasks": [], "events": []}
    )
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


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request) -> HTMLResponse:
    settings = getattr(request.app.state, "runtime_settings", None)
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "page": "tasks",
            "title": "Tasks",
            "tasks": [],
            "docker_mode": bool(settings and settings.docker_mode),
            "browser_automation_supported": bool(
                settings and settings.browser_automation_supported
            ),
        },
    )


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request) -> HTMLResponse:
    repo = getattr(request.app.state, "repository", None)
    accounts = repo.list_accounts() if repo is not None else []
    return templates.TemplateResponse(
        request,
        "accounts.html",
        {"page": "accounts", "title": "Accounts", "accounts": accounts},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    snapshot = build_health_snapshot()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "page": "settings",
            "title": "Settings",
            "checks": snapshot["checks"],
            "settings_ok": snapshot["ok"],
        },
    )
