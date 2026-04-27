from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"page": "dashboard", "title": "Dashboard", "stats": [], "tasks": [], "events": []},
    )


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"page": "tasks", "title": "Tasks", "tasks": []},
    )


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "accounts.html",
        {"page": "accounts", "title": "Accounts", "accounts": []},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"page": "settings", "title": "Settings", "checks": []},
    )
