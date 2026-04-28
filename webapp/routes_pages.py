from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from webapp.config_health import build_health_snapshot
from webapp.i18n import resolve_language, translator
from webapp.pool_sync import sync_pool_accounts

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _context(request: Request, page: str, title_key: str, **values):
    lang = resolve_language(request)
    t = translator(lang)
    return {
        "page": page,
        "title": t(title_key),
        "lang": lang,
        "t": t,
        **values,
    }


def _template_response(request: Request, template_name: str, context: dict) -> HTMLResponse:
    response = templates.TemplateResponse(request, template_name, context)
    if request.query_params.get("lang") in {"en", "zh"}:
        response.set_cookie("wa_lang", context["lang"], samesite="lax")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    repo = getattr(request.app.state, "repository", None)
    snapshot = (
        repo.dashboard_snapshot()
        if repo is not None
        else {"stats": {"running": 0, "queued": 0, "failed": 0, "succeeded": 0}, "tasks": [], "events": []}
    )
    return _template_response(
        request,
        "dashboard.html",
        _context(
            request,
            "dashboard",
            "dashboard.title",
            stats=snapshot["stats"],
            tasks=snapshot["tasks"],
            events=snapshot["events"],
        ),
    )


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request) -> HTMLResponse:
    repo = getattr(request.app.state, "repository", None)
    settings = getattr(request.app.state, "runtime_settings", None)
    return _template_response(
        request,
        "tasks.html",
        _context(
            request,
            "tasks",
            "tasks.title",
            tasks=(repo.dashboard_snapshot()["tasks"] if repo is not None else []),
            docker_mode=bool(settings and settings.docker_mode),
            browser_automation_supported=bool(
                settings and settings.browser_automation_supported
            ),
        ),
    )


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request) -> HTMLResponse:
    repo = getattr(request.app.state, "repository", None)
    pool_client = getattr(request.app.state, "pool_client", None)
    if repo is not None and pool_client is not None:
        try:
            sync_pool_accounts(repo, pool_client)
        except Exception:
            pass
    accounts = repo.list_accounts() if repo is not None else []
    return _template_response(
        request,
        "accounts.html",
        _context(request, "accounts", "accounts.title", accounts=accounts),
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    snapshot = build_health_snapshot()
    return _template_response(
        request,
        "settings.html",
        _context(
            request,
            "settings",
            "settings.title",
            checks=snapshot["checks"],
            settings_ok=snapshot["ok"],
        ),
    )
