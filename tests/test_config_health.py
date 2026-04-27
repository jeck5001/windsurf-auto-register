from webapp.config_health import build_health_snapshot


def test_build_health_snapshot_masks_secret_values(monkeypatch):
    monkeypatch.setenv("YYDS_MAIL_API_KEY", "secret-key")
    snapshot = build_health_snapshot()

    assert snapshot["checks"]["yyds_api_key"]["present"] is True
    assert snapshot["checks"]["yyds_api_key"]["display"] == "configured"
