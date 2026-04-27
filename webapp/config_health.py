from __future__ import annotations

import os

from webapp.env_loader import load_project_env
from webapp.runtime import load_runtime_settings


def build_health_snapshot() -> dict:
    load_project_env()
    settings = load_runtime_settings()
    checks = {
        "runtime_mode": {
            "present": True,
            "display": "docker" if settings.docker_mode else "local",
        },
        "browser_automation": {
            "present": settings.browser_automation_supported,
            "display": (
                "supported"
                if settings.browser_automation_supported
                else "unsupported in docker v1"
            ),
        },
        "yyds_api_key": {
            "present": bool(os.getenv("YYDS_MAIL_API_KEY")),
            "display": "configured" if os.getenv("YYDS_MAIL_API_KEY") else "missing",
        },
        "pool_url": {
            "present": bool(os.getenv("WINDSURF_POOL_URL")),
            "display": "configured" if os.getenv("WINDSURF_POOL_URL") else "missing",
        },
    }
    overall_ok = checks["yyds_api_key"]["present"] and checks["pool_url"]["present"]
    return {"ok": overall_ok, "checks": checks}
