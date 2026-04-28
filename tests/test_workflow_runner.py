from types import SimpleNamespace

from webapp.workflow_runner import WorkflowRequest, run_workflow_once
from windsurf_auth_replay import WorkflowError, generate_trial_checkout, resolve_registration_password


def test_run_workflow_once_emits_masked_events(monkeypatch):
    events: list[dict[str, str]] = []

    def fake_full_workflow(config, args):
        return {"mode": "full", "email": "demo@example.com", "ott": "ott$secret-token"}

    monkeypatch.setattr("webapp.workflow_runner.full_workflow", fake_full_workflow)
    monkeypatch.setattr("webapp.workflow_runner.build_config", lambda args: SimpleNamespace())

    result = run_workflow_once(
        WorkflowRequest(
            mode="full",
            email="",
            password="",
            account_count=1,
            generate_trial_link=False,
        ),
        on_event=events.append,
    )

    assert result["mode"] == "full"
    assert result["ott"].startswith("ott$")
    assert any(event["level"] == "info" for event in events)


def test_run_workflow_once_uses_env_backed_defaults(monkeypatch):
    events: list[dict[str, str]] = []

    monkeypatch.setenv("WINDSURF_POOL_URL", "http://pool.example")
    monkeypatch.setenv("YYDS_MAIL_API_KEY", "secret-key")

    captured = {}

    def fake_build_config(args):
        captured["pool_base_url"] = args.pool_base_url
        captured["yyds_api_key"] = args.yyds_api_key
        return SimpleNamespace(pool_base_url=args.pool_base_url, yyds_api_key=args.yyds_api_key)

    def fake_full_workflow(config, args):
        return {"mode": "full", "email": "demo@example.com", "ott": "ott$secret-token"}

    monkeypatch.setattr("webapp.workflow_runner.build_config", fake_build_config)
    monkeypatch.setattr("webapp.workflow_runner.full_workflow", fake_full_workflow)

    run_workflow_once(
        WorkflowRequest(
            mode="full",
            email="",
            password="",
            account_count=1,
            generate_trial_link=False,
        ),
        on_event=events.append,
    )

    assert captured["pool_base_url"] == "http://pool.example"
    assert captured["yyds_api_key"] == "secret-key"


def test_run_workflow_once_marks_web_requests_non_interactive(monkeypatch):
    events: list[dict[str, str]] = []
    captured = {}

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    def fake_build_config(args):
        captured["interactive"] = getattr(args, "interactive", None)
        return SimpleNamespace()

    def fake_full_workflow(config, args):
        return {"mode": "full", "email": "demo@example.com", "ott": "ott$secret-token"}

    monkeypatch.setattr("webapp.workflow_runner.build_config", fake_build_config)
    monkeypatch.setattr("webapp.workflow_runner.full_workflow", fake_full_workflow)

    run_workflow_once(
        WorkflowRequest(
            mode="full",
            email="",
            password="",
            account_count=1,
            generate_trial_link=False,
        ),
        on_event=events.append,
    )

    assert captured["interactive"] is False


def test_resolve_registration_password_generates_value_without_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("windsurf_auth_replay.generate_password", lambda length=16: "AutoPass123!")
    monkeypatch.setattr(
        "windsurf_auth_replay.prompt_password",
        lambda: (_ for _ in ()).throw(AssertionError("prompt_password should not be called")),
    )

    password = resolve_registration_password("")

    assert password == "AutoPass123!"


def test_resolve_registration_password_skips_prompt_when_interaction_disabled(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("windsurf_auth_replay.generate_password", lambda length=16: "AutoPass123!")
    monkeypatch.setattr(
        "windsurf_auth_replay.prompt_password",
        lambda: (_ for _ in ()).throw(AssertionError("prompt_password should not be called")),
    )

    password = resolve_registration_password("", interactive=False)

    assert password == "AutoPass123!"


def test_generate_trial_checkout_continues_when_eligibility_endpoint_errors(monkeypatch):
    config = SimpleNamespace()
    captured = {}

    class FakeWindsurf:
        def check_trial_eligibility(self, session_token, config):
            raise WorkflowError("检查 Trial 资格失败: an internal error occurred")

        def create_trial_checkout_url(self, session_token, turnstile_token, config):
            captured["session_token"] = session_token
            captured["turnstile_token"] = turnstile_token
            return "https://checkout.stripe.com/direct"

    monkeypatch.setattr(
        "windsurf_auth_replay.resolve_turnstile_token",
        lambda config: ("turnstile-token", "solver"),
    )

    result = generate_trial_checkout(
        FakeWindsurf(),
        config,
        session_token="session-plain",
    )

    assert result["trial_eligible"] is None
    assert result["trial_checkout_url"] == "https://checkout.stripe.com/direct"
    assert captured["session_token"] == "session-plain"
    assert captured["turnstile_token"] == "turnstile-token"
