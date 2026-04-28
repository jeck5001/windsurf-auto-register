from fastapi.testclient import TestClient

from turnstile_solver.app import app


def test_solver_returns_token(monkeypatch):
    monkeypatch.setattr(
        "turnstile_solver.app.solve_turnstile_request",
        lambda payload: "solver-token",
    )
    client = TestClient(app)

    response = client.post(
        "/solve",
        json={
            "site_url": "https://windsurf.com/billing/individual?plan=9",
            "sitekey": "",
            "browser_path": "",
            "timeout": 90,
            "headless": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"token": "solver-token"}


def test_solver_returns_detail_on_workflow_error(monkeypatch):
    def fail(payload):
        raise RuntimeError("solver boom")

    monkeypatch.setattr("turnstile_solver.app.solve_turnstile_request", fail)
    client = TestClient(app)

    response = client.post(
        "/solve",
        json={
            "site_url": "https://windsurf.com/billing/individual?plan=9",
            "sitekey": "",
            "browser_path": "",
            "timeout": 90,
            "headless": True,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "solver boom"}
