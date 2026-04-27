from types import SimpleNamespace

from webapp.workflow_runner import WorkflowRequest, run_workflow_once


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
