from __future__ import annotations

import os


def build_health_snapshot() -> dict:
    checks = {
        "yyds_api_key": {
            "present": bool(os.getenv("YYDS_MAIL_API_KEY")),
            "display": "configured" if os.getenv("YYDS_MAIL_API_KEY") else "missing",
        },
        "pool_url": {
            "present": bool(os.getenv("WINDSURF_POOL_URL")),
            "display": "configured" if os.getenv("WINDSURF_POOL_URL") else "missing",
        },
        "turnstile_mode": {
            "present": True,
            "display": "browser or token",
        },
    }
    overall_ok = all(item["present"] for key, item in checks.items() if key != "turnstile_mode")
    return {"ok": overall_ok, "checks": checks}
