# Docker Compose Admin Runtime Design

## Summary

Add a first-version `docker-compose` runtime for the Windsurf admin console so the management UI and its background task execution model can be started with one command.

This runtime should prioritize operational simplicity over maximum feature coverage. The first version must containerize the admin web app, its in-process task worker, and SQLite persistence, while explicitly excluding containerized browser automation for `trial-browser` and other `patchright`-dependent flows.

## Goals

- Start the admin console with `docker compose up --build`.
- Keep the runtime aligned with the current Python monolith architecture.
- Persist admin task data and account history to a host-mounted SQLite file.
- Load configuration from the project `.env` file without duplicating environment declarations in compose.
- Support non-browser task execution paths inside the container.
- Make unsupported browser-automation flows fail clearly instead of hanging or silently misbehaving.

## Non-Goals

- Containerize Chromium or fully support `patchright` browser automation in v1.
- Split the runtime into multiple services such as `web`, `worker`, `redis`, or `db`.
- Re-architect the current in-process queue into a distributed job system.
- Introduce Kubernetes, Helm, or production-grade orchestration concerns.

## User Intent

The user wants a practical `docker-compose` startup path for the new admin interface, with minimal setup friction and predictable persistence behavior.

## Product Direction

### Runtime Thesis

One service, one command, one data directory. The compose experience should feel like “clone, fill `.env`, run, open browser.”

### Operational Model

- A single `app` service runs the FastAPI admin console.
- The same container process space hosts the in-memory worker/thread model already used by the app.
- SQLite lives on the host under `./data`, mounted into the container.
- Environment variables come from the project root `.env`, mounted or loaded directly by compose.

### Failure Thesis

If a task depends on container-incompatible browser automation, the system should reject it with a clear user-facing message describing that the flow is not supported in Docker v1.

## Architecture

### Service Model

Use a single `app` service in `docker-compose.yml`.

Responsibilities:

- Install Python runtime dependencies.
- Serve FastAPI on port `8000`.
- Run the same admin process that owns page rendering, API endpoints, and the in-process task manager.

Reasoning:

- This matches the current codebase, which is still a Python monolith.
- It avoids premature separation of `web` and `worker`.
- It avoids SQLite locking complexity from multiple containers sharing the same database file.

### Storage Model

Persist the database file under the project directory:

- Host path: `./data`
- Container path: `/app/data`
- Database file: `/app/data/windsurf_admin.db`

Requirements:

- The application must default to that path when running in the container.
- The directory should be created automatically if it does not exist.
- The host-mounted directory must survive container recreation.

### Configuration Model

Use the project root `.env` file as the primary configuration source.

Requirements:

- `docker-compose.yml` should load environment variables from `.env`.
- The application should continue to support its existing `load_dotenv()` behavior for local non-container runs.
- Compose should not duplicate every environment variable in the YAML unless required for a small number of runtime defaults.

### Image Model

Add a single-purpose `Dockerfile` for the admin runtime.

Requirements:

- Base image: Python 3.10+ compatible slim image.
- Install runtime dependencies from `requirements.txt`.
- Copy application source into the image.
- Default command should start the admin app with `uvicorn`.
- No browser or desktop dependencies are required in v1.

## Admin Behavior in Docker

### Supported In-Container Flows

- Admin UI page rendering.
- Task creation and queue management.
- SQLite-backed persistence.
- Non-browser workflow paths that use standard Python/network execution.
- Viewing logs, account history, and settings health state.

### Unsupported In-Container Flows

- `trial-browser` mode.
- Browser fallback paths that rely on `patchright`.
- Any flow that requires local GUI/browser capabilities.

### UX Requirement for Unsupported Flows

The admin UI must make unsupported Docker flows explicit.

Acceptable first-version behavior:

- Block submission of unsupported modes in the UI when a Docker runtime flag is set.
- Or allow submission but immediately fail with a clear error such as:
  `Docker runtime does not support browser automation flows in v1. Run this task outside Docker or use a non-browser mode.`

The message must be operator-readable and must not look like a generic internal crash.

## Files to Add

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

## Files to Modify

- `README.md`
  Add compose startup and persistence instructions.
- `webapp/app_state.py` or equivalent runtime configuration layer
  Ensure the database path can default to `/app/data/windsurf_admin.db`.
- `webapp/workflow_runner.py` and/or task-validation layer
  Enforce the Docker v1 browser-automation restriction.
- Any config-health or settings view necessary to expose Docker runtime constraints clearly.

## Compose UX

### Primary Command

```bash
docker compose up --build
```

### Expected Result

- The admin server binds to `0.0.0.0:8000` inside the container.
- Host port `8000` maps to container port `8000`.
- The dashboard is reachable at `http://127.0.0.1:8000/dashboard`.

### Persistence Behavior

- `./data` is created locally if missing.
- `windsurf_admin.db` is created inside `./data` on first start.
- Task and account history survive `docker compose down` and container recreation as long as `./data` remains.

## Security and Secrets

- Secrets continue to come from `.env`.
- `.env` remains gitignored and host-owned.
- The settings page should still show only masked/presence-based summaries.
- The Docker setup must not bake secrets into the image.

## Error Handling

- Missing `.env` should produce a clear startup or settings-health signal.
- Missing required directories should be created or reported clearly.
- Unsupported browser flows must fail clearly and early.
- The compose startup path should not require interactive prompts.

## Documentation Requirements

`README.md` should include:

- Build and startup command.
- Data persistence location.
- How `.env` is used.
- Which flows are supported inside Docker v1.
- Which flows still require non-container execution.

## Testing Strategy

Implementation should verify:

- The app container builds successfully.
- `docker compose up` starts the admin server successfully.
- The app can create and use `/app/data/windsurf_admin.db`.
- The dashboard is reachable on host port `8000`.
- Unsupported browser automation tasks produce the intended message.

## Resolved Decisions

- Compose v1 uses a single service, not separate `web` and `worker` containers.
- Configuration comes from the project `.env`.
- SQLite persistence lives in `./data`.
- Browser automation is explicitly out of scope for Docker v1.
