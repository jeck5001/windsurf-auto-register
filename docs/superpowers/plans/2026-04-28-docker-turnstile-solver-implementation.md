# Docker Turnstile Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an internal `turnstile-solver` Docker service so the admin app can generate Windsurf `Trial` links entirely inside Docker.

**Architecture:** Keep the existing admin app as the only exposed service and add a private FastAPI solver service that returns Turnstile tokens over HTTP. The app continues using the existing `TURNSTILE_SOLVER_URL` path, while Docker Compose and GHCR builds expand from one service to two images.

**Tech Stack:** Python 3.14, FastAPI, patchright, uvicorn, pytest, Docker, Docker Compose, GitHub Actions GHCR publishing

---

## File Map

- Create: `turnstile_solver/__init__.py`
- Create: `turnstile_solver/app.py`
- Create: `turnstile_solver/service.py`
- Create: `turnstile_solver/models.py`
- Create: `tests/test_turnstile_solver.py`
- Create: `Dockerfile.turnstile-solver`
- Create: `docs/superpowers/plans/2026-04-28-docker-turnstile-solver-implementation.md`
- Modify: `windsurf_auth_replay.py`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.ghcr.yml`
- Modify: `.github/workflows/docker-build.yml`
- Modify: `tests/test_workflow_runner.py`
- Modify: `docs/superpowers/specs/2026-04-28-docker-turnstile-solver-design.md` only if implementation forces a design correction

### Task 1: Harden App-Side Solver Routing

**Files:**
- Modify: `windsurf_auth_replay.py`
- Modify: `tests/test_workflow_runner.py`

- [ ] **Step 1: Write the failing test for solver URL success path**

Add this test to `tests/test_workflow_runner.py`:

```python
def test_resolve_turnstile_token_uses_solver_url(monkeypatch):
    config = SimpleNamespace(
        turnstile_token="",
        turnstile_solver_url="http://turnstile-solver:8001/solve",
        turnstile_site_url="https://windsurf.com/billing/individual?plan=9",
        turnstile_sitekey="site-key",
        turnstile_browser_path="",
        turnstile_timeout=45,
        turnstile_headless=True,
        request_timeout=20,
        verify_ssl=True,
    )

    class FakeResponse:
        ok = True

        def json(self):
            return {"token": "solver-token"}

    captured = {}

    def fake_post(url, json, timeout, verify):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr("windsurf_auth_replay.requests.post", fake_post)

    token, source = resolve_turnstile_token(config)

    assert token == "solver-token"
    assert source == "solver_url"
    assert captured["url"] == "http://turnstile-solver:8001/solve"
```

- [ ] **Step 2: Run the targeted test**

Run:

```bash
../../.venv/bin/pytest -q tests/test_workflow_runner.py -k uses_solver_url
```

Expected: `PASS` if the current branch still supports solver URL correctly, otherwise a focused failure pointing at the request payload or source label.

- [ ] **Step 3: Write the failing test for solver URL error propagation**

Add this test to `tests/test_workflow_runner.py`:

```python
def test_resolve_turnstile_token_surfaces_solver_detail(monkeypatch):
    config = SimpleNamespace(
        turnstile_token="",
        turnstile_solver_url="http://turnstile-solver:8001/solve",
        turnstile_site_url="https://windsurf.com/billing/individual?plan=9",
        turnstile_sitekey="",
        turnstile_browser_path="",
        turnstile_timeout=45,
        turnstile_headless=True,
        request_timeout=20,
        verify_ssl=True,
    )

    class FakeResponse:
        ok = False
        status_code = 502
        text = '{"detail":"solver timed out"}'

        def json(self):
            return {"detail": "solver timed out"}

    monkeypatch.setattr("windsurf_auth_replay.requests.post", lambda *args, **kwargs: FakeResponse())

    try:
        resolve_turnstile_token(config)
    except WorkflowError as exc:
        assert str(exc) == "请求外部 Turnstile solver失败: solver timed out"
    else:
        raise AssertionError("expected WorkflowError")
```

- [ ] **Step 4: Run the targeted error test**

Run:

```bash
../../.venv/bin/pytest -q tests/test_workflow_runner.py -k surfaces_solver_detail
```

Expected: FAIL only if the code path is not preserving solver-side error detail.

- [ ] **Step 5: Write the failing test that Docker never falls back to browser after solver failure**

Add this test to `tests/test_workflow_runner.py`:

```python
def test_generate_trial_checkout_does_not_browser_fallback_when_solver_url_fails(monkeypatch):
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    config = SimpleNamespace()
    captured = {"browser_called": False}

    class FakeWindsurf:
        def check_trial_eligibility(self, session_token, config):
            return True

        def create_trial_checkout_url(self, session_token, turnstile_token, config):
            raise AssertionError("should not reach checkout call")

    monkeypatch.setattr(
        "windsurf_auth_replay.resolve_turnstile_token",
        lambda config: (_ for _ in ()).throw(WorkflowError("solver unavailable")),
    )
    monkeypatch.setattr(
        "windsurf_auth_replay._browser_trial_fallback",
        lambda *args, **kwargs: captured.__setitem__("browser_called", True),
    )

    try:
        generate_trial_checkout(
            FakeWindsurf(),
            config,
            session_token="session-plain",
            email="account@example.com",
            password="VisiblePass123",
        )
    except WorkflowError as exc:
        assert str(exc) == "solver unavailable"
    else:
        raise AssertionError("expected WorkflowError")

    assert captured["browser_called"] is False
```

- [ ] **Step 6: Run the new fallback test**

Run:

```bash
../../.venv/bin/pytest -q tests/test_workflow_runner.py -k solver_url_fails
```

Expected: FAIL if Docker paths still try browser fallback after solver failure.

- [ ] **Step 7: Implement the minimal app-side behavior**

Update `windsurf_auth_replay.py` so these branches stay true:

```python
def resolve_turnstile_token(config: AppConfig) -> tuple[str, str]:
    if config.turnstile_token:
        return config.turnstile_token, "env"
    if config.turnstile_solver_url:
        response = requests.post(
            config.turnstile_solver_url,
            json={
                "site_url": config.turnstile_site_url,
                "sitekey": config.turnstile_sitekey,
                "browser_path": config.turnstile_browser_path,
                "timeout": config.turnstile_timeout,
                "headless": config.turnstile_headless,
            },
            timeout=config.request_timeout,
            verify=config.verify_ssl,
        )
        raise_for_http(response, "请求外部 Turnstile solver")
        payload = maybe_json(response)
        if not isinstance(payload, dict) or not payload.get("token"):
            raise WorkflowError("请求外部 Turnstile solver 失败: 响应里没有 token")
        return str(payload["token"]), "solver_url"
```

and:

```python
except WorkflowError as api_exc:
    can_browser_fallback = bool(email and password) and not env_bool("RUNNING_IN_DOCKER", False)
    if not can_browser_fallback:
        raise
```

- [ ] **Step 8: Run all workflow tests**

Run:

```bash
../../.venv/bin/pytest -q tests/test_workflow_runner.py
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_workflow_runner.py windsurf_auth_replay.py
git commit -m "fix: route docker turnstile requests through solver"
```

### Task 2: Build the Solver Service

**Files:**
- Create: `turnstile_solver/__init__.py`
- Create: `turnstile_solver/models.py`
- Create: `turnstile_solver/service.py`
- Create: `turnstile_solver/app.py`
- Create: `tests/test_turnstile_solver.py`

- [ ] **Step 1: Write the failing API contract test**

Create `tests/test_turnstile_solver.py` with:

```python
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
```

- [ ] **Step 2: Run the solver token test**

Run:

```bash
../../.venv/bin/pytest -q tests/test_turnstile_solver.py -k returns_token
```

Expected: FAIL with import error because the solver package does not exist yet.

- [ ] **Step 3: Write the failing solver error contract test**

Append:

```python
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
```

- [ ] **Step 4: Run the solver error test**

Run:

```bash
../../.venv/bin/pytest -q tests/test_turnstile_solver.py -k returns_detail
```

Expected: FAIL until the app is created and maps exceptions into `400`.

- [ ] **Step 5: Create the request model**

Create `turnstile_solver/models.py`:

```python
from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    site_url: str
    sitekey: str = ""
    browser_path: str = ""
    timeout: int = Field(default=90, ge=5, le=300)
    headless: bool = True
```

- [ ] **Step 6: Create the service wrapper**

Create `turnstile_solver/service.py`:

```python
from windsurf_auth_replay import solve_turnstile_token_with_options

from turnstile_solver.models import SolveRequest


def solve_turnstile_request(payload: SolveRequest) -> str:
    return solve_turnstile_token_with_options(
        site_url=payload.site_url,
        sitekey=payload.sitekey,
        browser_path=payload.browser_path,
        timeout=payload.timeout,
        headless=payload.headless,
    )
```

- [ ] **Step 7: Create the FastAPI app**

Create `turnstile_solver/app.py`:

```python
from fastapi import FastAPI, HTTPException

from turnstile_solver.models import SolveRequest
from turnstile_solver.service import solve_turnstile_request

app = FastAPI(title="Turnstile Solver")


@app.post("/solve")
def solve(payload: SolveRequest) -> dict[str, str]:
    try:
        token = solve_turnstile_request(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"token": token}
```

Create `turnstile_solver/__init__.py`:

```python
# Package marker for the Turnstile solver service.
```

- [ ] **Step 8: Run solver tests**

Run:

```bash
../../.venv/bin/pytest -q tests/test_turnstile_solver.py
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add turnstile_solver tests/test_turnstile_solver.py
git commit -m "feat: add internal turnstile solver service"
```

### Task 3: Package the Solver for Docker

**Files:**
- Create: `Dockerfile.turnstile-solver`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.ghcr.yml`

- [ ] **Step 1: Write the failing compose topology test as a text assertion**

Add this test to `tests/test_pages.py` only if you want code-level protection for compose content; otherwise use a direct file check in the shell. Preferred direct check:

```bash
rg -n "turnstile-solver|TURNSTILE_SOLVER_URL" docker-compose.yml docker-compose.ghcr.yml
```

Expected: no matches before the change.

- [ ] **Step 2: Add the solver Dockerfile**

Create `Dockerfile.turnstile-solver`:

```dockerfile
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxshmfence1 \
    libgtk-3-0 \
    ca-certificates \
    fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m patchright install chromium

COPY . .

EXPOSE 8001

CMD ["uvicorn", "turnstile_solver.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 3: Update local compose**

Update `docker-compose.yml` to:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env
    environment:
      RUNNING_IN_DOCKER: "1"
      WINDSURF_ADMIN_DB_PATH: /app/data/windsurf_admin.db
      TURNSTILE_SOLVER_URL: http://turnstile-solver:8001/solve
    depends_on:
      - turnstile-solver
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  turnstile-solver:
    build:
      context: .
      dockerfile: Dockerfile.turnstile-solver
    restart: unless-stopped
```

- [ ] **Step 4: Update GHCR compose**

Update `docker-compose.ghcr.yml` to:

```yaml
services:
  app:
    image: ghcr.io/jeck5001/windsurf-auto-register:latest
    container_name: windsurf-auto-register
    env_file:
      - .env
    environment:
      RUNNING_IN_DOCKER: "1"
      WINDSURF_ADMIN_DB_PATH: /app/data/windsurf_admin.db
      TURNSTILE_SOLVER_URL: http://turnstile-solver:8001/solve
    depends_on:
      - turnstile-solver
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  turnstile-solver:
    image: ghcr.io/jeck5001/windsurf-auto-register-turnstile-solver:latest
    container_name: windsurf-auto-register-turnstile-solver
    restart: unless-stopped
```

- [ ] **Step 5: Validate compose files**

Run:

```bash
docker compose config > /tmp/windsurf-compose.rendered.yml
docker compose -f docker-compose.ghcr.yml config > /tmp/windsurf-compose-ghcr.rendered.yml
```

Expected: both commands exit `0`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile.turnstile-solver docker-compose.yml docker-compose.ghcr.yml
git commit -m "feat: add docker turnstile solver service"
```

### Task 4: Publish Both Images from GitHub Actions

**Files:**
- Modify: `.github/workflows/docker-build.yml`

- [ ] **Step 1: Write the failing workflow check**

Run:

```bash
rg -n "windsurf-auto-register-turnstile-solver|Dockerfile.turnstile-solver" .github/workflows/docker-build.yml
```

Expected: no matches before the change.

- [ ] **Step 2: Extend metadata for the solver image**

Update `.github/workflows/docker-build.yml` to add a second metadata step:

```yaml
      - name: Extract Solver Docker metadata
        id: solver_meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository_owner }}/windsurf-auto-register-turnstile-solver
          tags: |
            type=raw,value=latest
            type=ref,event=branch
            type=sha,prefix=sha-
```

- [ ] **Step 3: Add the solver build-and-push step**

Append:

```yaml
      - name: Build and optionally push Solver Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile.turnstile-solver
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.solver_meta.outputs.tags }}
          labels: ${{ steps.solver_meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 4: Validate workflow syntax**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
yaml.safe_load(Path(".github/workflows/docker-build.yml").read_text())
print("ok")
PY
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/docker-build.yml
git commit -m "ci: publish turnstile solver image"
```

### Task 5: End-to-End Verification and Deployment Notes

**Files:**
- Modify: `tests/test_workflow_runner.py` if a final edge-case test is still missing
- Modify: `docs/superpowers/specs/2026-04-28-docker-turnstile-solver-design.md` only if behavior changed

- [ ] **Step 1: Run the full Python test suite**

Run:

```bash
../../.venv/bin/pytest -q
```

Expected: PASS

- [ ] **Step 2: Build the solver image locally**

Run:

```bash
docker build -f Dockerfile.turnstile-solver -t windsurf-turnstile-solver:test .
```

Expected: image builds successfully, including browser install step.

- [ ] **Step 3: Render and boot the two-service local stack**

Run:

```bash
docker compose up -d --build
docker compose ps
```

Expected: both `app` and `turnstile-solver` show `Up`.

- [ ] **Step 4: Smoke test the solver directly from inside the app network**

Run:

```bash
docker compose exec app python - <<'PY'
import requests
r = requests.post("http://turnstile-solver:8001/solve", json={
    "site_url": "https://windsurf.com/billing/individual?plan=9",
    "sitekey": "",
    "browser_path": "",
    "timeout": 10,
    "headless": True,
}, timeout=30)
print(r.status_code)
print(r.text[:400])
PY
```

Expected: `200` with `token`, or a controlled `400` with a readable `detail`. No connection failure.

- [ ] **Step 5: Push the branch and watch both GHCR builds**

Run:

```bash
git push fork codex/windsurf-admin-ui
gh run list -R jeck5001/windsurf-auto-register --branch codex/windsurf-admin-ui --limit 5
```

Expected: workflow starts and publishes both images.

- [ ] **Step 6: Commit any final doc or test adjustments**

```bash
git add tests/test_workflow_runner.py docs/superpowers/specs/2026-04-28-docker-turnstile-solver-design.md
git commit -m "docs: finalize docker turnstile solver rollout notes"
```

## Self-Review

- Spec coverage:
  - Docker-internal `Trial` token generation is covered by Tasks 1-3.
  - Internal-only solver networking is covered by Task 3.
  - GHCR dual-image publishing is covered by Task 4.
  - Error handling and non-500 failures are covered by Tasks 1, 2, and 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or cross-task “same as above” shortcuts remain.
- Type consistency:
  - `SolveRequest`, `solve_turnstile_request`, `turnstile_solver.app:app`, and `TURNSTILE_SOLVER_URL` are named consistently across tasks.
