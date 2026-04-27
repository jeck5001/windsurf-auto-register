from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from typing import Any, Callable

from webapp.runtime import RuntimeSettings, load_runtime_settings
from windsurf_auth_replay import (
    WorkflowError,
    build_config,
    clear_stop_request,
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
        base_url="https://windsurf.com",
        pool_base_url="",
        pool_upload_mode="auth",
        pool_dashboard_password="",
        pool_ssh_key_path="~/.ssh/id_ed25519",
        pool_ssh_user="root",
        yyds_base_url="https://maliapi.215.im/v1",
        yyds_api_key="",
        yyds_domain="",
        yyds_subdomain="",
        yyds_local_part="",
        request_timeout=20,
        poll_timeout=60,
        poll_interval=5,
        max_attempts=5,
        insecure=False,
        debug=False,
        generate_trial_link=request.generate_trial_link,
        turnstile_token="",
        turnstile_site_url="",
        turnstile_sitekey="",
        turnstile_solver_url="",
        turnstile_browser_path="",
        turnstile_timeout=90,
        headed_turnstile=False,
        login_url="",
        billing_url="",
        headless_browser=False,
        trial_success_url="",
        trial_cancel_url="",
        trial_plan_id="",
        output_json="",
        include_secrets_in_output=False,
        show_secrets=False,
    )


def run_workflow_once(
    request: WorkflowRequest,
    on_event: Callable[[dict[str, str]], None],
) -> dict[str, Any]:
    settings = load_runtime_settings()
    validate_runtime_support(request, settings)
    args = _build_args(request)
    config = build_config(args)
    token = set_event_callback(on_event)
    clear_stop_request()
    try:
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
