from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from typing import Any, Callable

from webapp.env_loader import load_project_env
from webapp.runtime import RuntimeSettings, load_runtime_settings
from windsurf_auth_replay import (
    WorkflowError,
    build_config,
    clear_stop_request,
    env_bool,
    env_int,
    env_str,
    full_workflow,
    reset_event_callback,
    set_event_callback,
    summarize_result,
    trial_browser_workflow,
    trial_workflow,
    upload_only_workflow,
)


@dataclass
class WorkflowRequest:
    mode: str
    email: str
    password: str
    account_count: int
    generate_trial_link: bool


def validate_runtime_support(
    request: WorkflowRequest,
    settings: RuntimeSettings,
) -> None:
    if not settings.docker_mode:
        return
    if request.mode == "trial-browser" or request.generate_trial_link:
        raise WorkflowError(
            "Docker runtime does not support browser automation flows in v1. "
            "Run this task outside Docker or use a non-browser mode."
        )


def _build_args(request: WorkflowRequest) -> Namespace:
    return Namespace(
        mode=request.mode,
        email=request.email,
        name="",
        password=request.password,
        label="",
        ott="",
        session_token="",
        account_count=request.account_count,
        base_url=env_str("WINDSURF_BASE_URL", "https://windsurf.com"),
        pool_base_url=env_str("WINDSURF_POOL_URL"),
        pool_upload_mode=env_str("WINDSURF_POOL_UPLOAD_MODE", "auth"),
        pool_dashboard_password=env_str("WINDSURF_POOL_DASHBOARD_PASSWORD"),
        pool_ssh_key_path=env_str("WINDSURF_POOL_SSH_KEY_PATH", "~/.ssh/id_ed25519"),
        pool_ssh_user=env_str("WINDSURF_POOL_SSH_USER", "root"),
        yyds_base_url=env_str("YYDS_MAIL_BASE_URL", "https://maliapi.215.im/v1"),
        yyds_api_key=env_str("YYDS_MAIL_API_KEY"),
        yyds_domain=env_str("YYDS_MAIL_DOMAIN"),
        yyds_subdomain=env_str("YYDS_MAIL_SUBDOMAIN"),
        yyds_local_part=env_str("YYDS_MAIL_LOCAL_PART"),
        request_timeout=env_int("REQUEST_TIMEOUT", 20),
        poll_timeout=env_int("POLL_TIMEOUT", 60),
        poll_interval=env_int("POLL_INTERVAL", 5),
        max_attempts=env_int("MAX_ATTEMPTS", 5),
        insecure=not env_bool("VERIFY_SSL", True),
        debug=env_bool("DEBUG", False),
        generate_trial_link=request.generate_trial_link,
        turnstile_token=env_str("WINDSURF_TURNSTILE_TOKEN"),
        turnstile_site_url=env_str("WINDSURF_TURNSTILE_SITE_URL"),
        turnstile_sitekey=env_str("WINDSURF_TURNSTILE_SITEKEY"),
        turnstile_solver_url=env_str("TURNSTILE_SOLVER_URL"),
        turnstile_browser_path=env_str("TURNSTILE_BROWSER_PATH"),
        turnstile_timeout=env_int("TURNSTILE_TIMEOUT", 90),
        headed_turnstile=not env_bool("TURNSTILE_HEADLESS", True),
        login_url="",
        billing_url="",
        headless_browser=False,
        trial_success_url=env_str("WINDSURF_TRIAL_SUCCESS_URL"),
        trial_cancel_url=env_str("WINDSURF_TRIAL_CANCEL_URL"),
        trial_plan_id=env_str("WINDSURF_TRIAL_PLAN_ID"),
        output_json=env_str("OUTPUT_JSON"),
        include_secrets_in_output=False,
        show_secrets=env_bool("SHOW_SECRETS", False),
    )


def run_workflow_once(
    request: WorkflowRequest,
    on_event: Callable[[dict[str, str]], None],
) -> dict[str, Any]:
    load_project_env()
    settings = load_runtime_settings()
    token = set_event_callback(on_event)
    clear_stop_request()
    try:
        validate_runtime_support(request, settings)
        args = _build_args(request)
        config = build_config(args)
        on_event({"level": "info", "message": f"starting mode={request.mode}"})
        if request.mode == "upload":
            result = upload_only_workflow(config, args)
        elif request.mode == "trial":
            result = trial_workflow(config, args)
        elif request.mode == "trial-browser":
            result = trial_browser_workflow(config, args)
        else:
            result = full_workflow(config, args)
        return summarize_result(result, include_secrets=False)
    except WorkflowError as exc:
        on_event({"level": "error", "message": str(exc)})
        raise
    finally:
        reset_event_callback(token)
        clear_stop_request()
