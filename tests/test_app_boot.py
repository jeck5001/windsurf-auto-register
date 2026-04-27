import os
from fastapi.testclient import TestClient
from types import SimpleNamespace

from webapp.app import app
from webapp.app_state import configure_app_state


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_root_redirects_to_dashboard():
    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


def test_configure_app_state_loads_env_from_ancestor_repo_root(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    worktree_root = repo_root / ".worktrees" / "feature"
    worktree_root.mkdir(parents=True)
    (repo_root / ".env").write_text(
        "WINDSURF_POOL_URL=http://pool.example\nYYDS_MAIL_API_KEY=secret-key\n",
        encoding="utf-8",
    )
    (worktree_root / ".env").write_text(
        "WINDSURF_POOL_URL=http://stale.example\nYYDS_MAIL_API_KEY=stale-key\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(worktree_root)
    monkeypatch.delenv("WINDSURF_POOL_URL", raising=False)
    monkeypatch.delenv("YYDS_MAIL_API_KEY", raising=False)

    fake_app = SimpleNamespace(state=SimpleNamespace())
    fake_app.state.db_path = worktree_root / "admin.db"

    configure_app_state(fake_app)

    assert fake_app.state.pool_client is not None
    assert os.getenv("WINDSURF_POOL_URL") == "http://pool.example"
