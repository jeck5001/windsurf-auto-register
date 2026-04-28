# Docker Turnstile Solver Design

Date: 2026-04-28
Branch: `codex/windsurf-admin-ui`

## Goal

Allow `Trial` links to be generated while the admin app is running inside Docker on NAS.

The current Docker runtime cannot solve Cloudflare Turnstile locally because the main app container does not ship a browser runtime. The desired result is:

- `Trial` generation works end-to-end inside Docker.
- The public admin UI remains a single exposed web service.
- Browser automation is isolated away from the main app container.
- Failures become explicit API errors instead of unhandled `500` crashes.

## Non-Goals

- Reworking the existing local desktop flow.
- Exposing a browser automation endpoint publicly to the NAS LAN or internet.
- Refactoring the full registration workflow outside the minimum changes needed for solver integration.
- Changing the existing account/task UI behavior beyond the backend support needed for Docker `Trial`.

## Requirements

### Functional

1. When the app runs in Docker, `Trial` link generation must be able to obtain a Turnstile token without relying on a browser inside the main app container.
2. The admin app must keep using the existing `TURNSTILE_SOLVER_URL` contract so the workflow layer does not need a second solver protocol.
3. The Docker Compose deployment must start both the admin app and a private solver service.
4. The solver service must accept the same inputs the app already sends:
   - `site_url`
   - `sitekey`
   - `browser_path`
   - `timeout`
   - `headless`
5. The solver service must return either:
   - `200 {"token": "..."}`
   - non-`200` with a JSON `detail` message
6. `Trial` generation errors in Docker must surface as handled `400`-class workflow errors rather than unhandled server exceptions.

### Operational

1. Only the app service is exposed through a host port.
2. The solver service is reachable only on the Compose internal network.
3. GHCR builds must publish images needed for this deployment model.
4. The NAS deployment path must remain simple: pull updated images and run `docker-compose up -d`.

## Architecture

### Services

#### 1. `app`

The existing FastAPI admin app remains the only user-facing service.

Responsibilities:

- Render admin UI
- Manage tasks and accounts
- Run Windsurf registration and trial workflows
- Request Turnstile tokens from an external solver URL when configured

Docker behavior:

- In Compose, `TURNSTILE_SOLVER_URL` is set to the internal solver service URL.
- The app no longer depends on local browser automation to support Docker `Trial`.

#### 2. `turnstile-solver`

A new internal-only FastAPI service dedicated to Turnstile solving.

Responsibilities:

- Receive a solver request from the app
- Launch browser automation inside its own container
- Open the billing page
- Extract the Turnstile token
- Return the token as JSON

Isolation rationale:

- Browser runtime dependencies stay out of the main app image.
- Solver crashes or browser issues are operationally isolated.
- Browser-specific image updates do not require redesigning the app container.

## Data Flow

### Docker `Trial` Flow

1. User clicks `Trial` in the admin UI.
2. The app resolves the account session token and enters `generate_trial_checkout()`.
3. The app checks trial eligibility.
4. The app calls `resolve_turnstile_token()`.
5. Because `TURNSTILE_SOLVER_URL` is configured in Docker Compose, the app sends an HTTP request to `turnstile-solver`.
6. The solver container opens the target page and obtains a Turnstile token.
7. The solver returns `{"token":"..."}`.
8. The app uses that token to call the Windsurf subscription endpoint and generate the Stripe Checkout URL.
9. The app stores the generated `trial_checkout_url` and returns success to the UI.

### Failure Flow

1. If the solver cannot launch a browser, load the page, or obtain a token, it returns a structured error.
2. The app maps that solver failure into a handled workflow error.
3. The API returns a user-visible `400` error payload instead of an unhandled `500`.

## Interface Design

### Solver API

Endpoint:

- `POST /solve`

Request JSON:

```json
{
  "site_url": "https://windsurf.com/billing/individual?plan=9",
  "sitekey": "",
  "browser_path": "",
  "timeout": 90,
  "headless": true
}
```

Success response:

```json
{
  "token": "cf-turnstile-response-token"
}
```

Failure response:

```json
{
  "detail": "human readable error"
}
```

Notes:

- `browser_path` stays accepted for protocol compatibility, but the solver container will typically ignore host-specific paths.
- The endpoint remains intentionally narrow so the app can reuse its current solver client code path.

## Implementation Scope

### New Files

1. A new solver service module, likely under a dedicated package such as `turnstile_solver/`.
2. A solver entrypoint FastAPI app.
3. A dedicated solver `Dockerfile`.
4. Optional dedicated solver requirements file if shared app dependencies are not a clean fit.

### Existing Files To Update

1. `docker-compose.yml`
2. `docker-compose.ghcr.yml`
3. `.github/workflows/...` Docker build workflow
4. `windsurf_auth_replay.py`
5. Tests covering workflow and Docker behavior
6. Deployment docs for NAS usage

## Compose Design

### Local Build Compose

`docker-compose.yml` should define:

- `app`
- `turnstile-solver`

`app` environment additions:

- `RUNNING_IN_DOCKER=1`
- `TURNSTILE_SOLVER_URL=http://turnstile-solver:8001/solve`

`turnstile-solver` behavior:

- no host port mapping required
- internal container port only
- restart policy aligned with the app

### GHCR Pull Compose

`docker-compose.ghcr.yml` should mirror the same two-service topology using published images:

- `ghcr.io/jeck5001/windsurf-auto-register:latest`
- a new solver image such as `ghcr.io/jeck5001/windsurf-auto-register-turnstile-solver:latest`

The NAS user experience remains:

```yaml
services:
  app:
    ...
  turnstile-solver:
    ...
```

with only `app` exposed to the host.

## CI/CD

The GitHub Actions Docker workflow must build and push:

1. Main app image
2. Solver image

Options:

- Single workflow with two image builds and two tags
- Single Dockerfile with multiple targets
- Separate Dockerfiles with a matrix build

Recommended approach:

- Keep separate Dockerfiles or explicit targets for clarity.
- Publish a distinct solver image name so Compose configuration is obvious and operational debugging is simpler.

## Error Handling

### App Side

- If `TURNSTILE_SOLVER_URL` is configured and the solver returns an HTTP error, preserve the returned `detail` when raising the workflow error.
- Do not silently fall back to local browser automation in Docker when a solver URL is configured but fails.
- Preserve current behavior for local non-Docker use.

### Solver Side

- Wrap browser startup failures.
- Wrap page-load and token-timeout failures.
- Return concise error text suitable for UI display and log inspection.

## Security Considerations

1. The solver must not be exposed through a NAS host port by default.
2. The solver handles only token-solving requests and returns only tokens or errors.
3. No account credentials should be persisted by the solver.
4. Logs should avoid dumping full sensitive values unless the project already explicitly opts into secret visibility.

## Testing

### Unit Tests

1. App-side tests for:
   - solver URL branch success
   - solver URL branch failure
   - Docker path not falling back incorrectly
2. Solver-side tests for:
   - request validation
   - token response format
   - error response format

### Integration Confidence

1. Compose-level manual validation:
   - `app` can reach `turnstile-solver`
   - `Trial` click produces a checkout URL in Docker
2. GHCR image validation:
   - both images build successfully in CI

## Rollout Plan

1. Add solver service code and tests.
2. Add solver image build.
3. Wire Compose files to include the internal solver service.
4. Update NAS deployment documentation.
5. Verify the Docker `Trial` flow end-to-end.

## Risks

1. Browser automation in containers can be sensitive to missing system libraries.
2. Cloudflare challenge behavior may differ between environments and require iterative selector hardening.
3. Solver startup time may be noticeable if the browser is launched on every request.

## Follow-Up Considerations

Not required for the first implementation:

- browser/context reuse inside the solver for lower latency
- health endpoint for solver diagnostics
- optional authentication between `app` and `turnstile-solver` if deployment scope broadens later
