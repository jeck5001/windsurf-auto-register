# Windsurf Admin UI Design

## Summary

Build a web-based admin interface for `windsurf-auto-register` so an operator can manage registration runs from a browser instead of driving the Python scripts manually. The UI should prioritize two jobs:

1. Control task execution for account registration and trial-link generation.
2. Monitor runtime health, failures, queue state, and recent outputs in real time.

The interface will use a multi-page admin structure with a low-glare light theme optimized for long sessions and dry-eye comfort.

## Goals

- Replace command-line-only operation with a browser management surface.
- Make task creation and batch execution the primary workflow.
- Surface operational state immediately on the dashboard.
- Keep configuration management available without making it the home-screen focus.
- Design the first version so it can be implemented incrementally on top of the current Python toolchain.

## Non-Goals

- Rebuild the existing automation logic in the UI layer.
- Add account analytics, billing, or multi-user permission systems in the first version.
- Design a marketing site or public-facing frontend.
- Optimize for mobile-first operation. Mobile support should be readable, but desktop is the primary target.

## Users

Primary user: a single operator running account registration batches, trial generation, and OTT uploads for operational purposes.

User needs:

- Start a new run quickly.
- See whether a batch is healthy or failing.
- Inspect recent logs without opening terminal output.
- Retry failures without rebuilding the entire batch manually.
- Check whether configuration is valid before starting a run.

## Product Direction

### Visual Thesis

A restrained operational workspace: calm light surfaces, strong typography, soft panel boundaries, and one darker inset region for live logs and urgent runtime context.

### Content Plan

- `Dashboard`: immediate operational awareness.
- `Tasks`: task creation and task lifecycle management.
- `Accounts`: registered account history and output status.
- `Settings`: provider, API, and runtime configuration.

### Interaction Thesis

- Fast, low-friction task launch from a dedicated Tasks page.
- Dashboard panels that update in place for queue and status awareness.
- A darker live-log area that visually anchors troubleshooting without forcing the whole app into dark mode.

## Information Architecture

### Primary Navigation

- `Dashboard`
- `Tasks`
- `Accounts`
- `Settings`

### Page Responsibilities

#### Dashboard

Purpose: answer “what is happening right now?”

Content:

- KPI strip for active runs, success rate, queue depth, and recent failure count.
- Active and queued task list.
- Runtime health panels for mailbox availability, upload status, and retry pressure.
- Live log stream.
- Recent run summary or last completed tasks.

This page is a command center, not a full editing surface. It should support quick navigation into a task or logs, but not contain the full task-builder form.

#### Tasks

Purpose: answer “what should I run next?”

Content:

- Task creation form.
- Mode selection: `full` vs `trial`.
- Batch controls: account count, retry policy, optional trial-link generation, concurrency controls if supported by backend.
- Start, stop, pause, retry-failed actions.
- Task table with status filters and bulk actions.

This is the primary operating surface.

#### Accounts

Purpose: answer “what did the system produce?”

Content:

- Registered account history.
- OTT upload status.
- Trial link generation result.
- Search/filter by email, mode, time, success/failure.
- Quick access to per-account details and failure reasons.

#### Settings

Purpose: answer “is the environment ready and correctly configured?”

Content:

- YYDS Mail provider settings.
- Windsurf Pool API settings.
- Trial/Turnstile settings.
- Browser/runtime settings.
- Environment health checks and secret presence indicators.

Settings should make configuration state legible without exposing raw secrets unnecessarily.

## Dashboard Layout

Recommended layout: `Command Center`

Structure:

1. Left rail navigation with the four primary pages.
2. Top bar with search or quick filter, run-state controls, environment summary, and a primary action entry point.
3. First content row: KPI cards.
4. Main content grid:
   - Left column: active/queued tasks.
   - Middle column: operational health and summarized issues.
   - Right column: live logs in a darker inset panel.

Reasoning:

- This balances control and monitoring instead of overcommitting to a monitoring wall.
- It keeps the user’s two priorities, task control and runtime monitoring, in the same visual plane.
- It avoids pushing the task workflow entirely out of sight while still preserving strong operational context.

## Tasks Layout

The Tasks page should be denser and more workflow-focused than Dashboard.

Recommended structure:

- Upper section: task builder form.
- Adjacent or inline controls: start/stop/retry actions.
- Main lower section: task runs table with filters, status chips, and row actions.
- Optional side panel or drawer: details for selected task, including logs and generated outputs.

The Tasks page should own the full “create and manage a batch” workflow. Dashboard only links into it.

## Visual Design Rules

### Theme

- Default theme: low-glare light.
- Backgrounds should use soft gray or warm-gray surfaces instead of pure white.
- Text should remain high-contrast and readable.
- Dark mode can exist later as an option, but should not be the default.

### Contrast and Comfort

- Avoid harsh white backgrounds.
- Avoid light-gray text on gray panels.
- Keep the log surface darker to help segmentation and fast parsing.
- Use clear spacing and stronger hierarchy instead of heavy borders everywhere.

### Style

- Calm, professional, and tool-like.
- No marketing hero language.
- No dashboard-card mosaic as the only design language.
- Prefer layout, typography, and restrained surfaces over decorative chrome.

## Content Strategy

Copy should read like utility software, not marketing.

Examples:

- Good: `Active Runs`, `Queue Depth`, `Upload Failures`, `Mailbox Status`, `Last Sync`
- Bad: vague promotional or executive-summary headlines that do not help the operator act

If a section does not help an operator operate, monitor, or decide, it should not be on the page.

## Data and Backend Implications

The current repository is a Python CLI tool. The UI should be designed to sit on top of a lightweight web management layer rather than replacing the automation internals.

Likely backend capabilities needed for implementation:

- Launch a run with structured parameters.
- Stream or poll runtime logs.
- Persist task status and results.
- Expose account history and result objects.
- Read configuration-health state safely.

This design assumes the first implementation may begin with local, single-user execution and a simple persistence model.

## Error Handling

- Failed tasks must show a short reason in list views and a fuller explanation in detail views.
- Configuration validation errors should appear before run start whenever possible.
- Runtime log entries should clearly differentiate info, warning, and failure states.
- Empty states should explain what the operator can do next.

## Responsive Behavior

- Desktop-first design.
- On narrower screens, the three-column dashboard should collapse into a readable stacked layout.
- Logs should remain accessible without forcing horizontal scrolling.
- Primary task actions must remain easy to reach on laptop-sized screens.

## Accessibility

- Strong text contrast on all primary reading surfaces.
- Keyboard-focus visibility for navigation, actions, and table rows.
- Clear status labels, not color-only state encoding.
- Body text and controls should avoid tiny sizing because the target usage is long-session monitoring.

## Testing Strategy For UI Implementation

When implemented, validate:

- Dashboard readability over long sessions.
- Task creation and execution flow from the browser.
- Status updates and live log rendering under active runs.
- Failure and empty-state clarity.
- Responsive layout on common desktop and small-laptop widths.

## Recommended Implementation Sequence

1. Establish the web shell and shared layout.
2. Implement Dashboard with mocked or adapter-backed data.
3. Implement Tasks page and task-control workflow.
4. Implement Accounts history.
5. Implement Settings and environment validation.
6. Replace mocked data with live backend integration.

## Open Assumptions Resolved

- The first version is multi-page, not single-page-only.
- The default visual direction is low-glare light mode for eye comfort.
- The dashboard uses the balanced `Command Center` layout.
- `Tasks` is the primary operating page.
- `Settings` is secondary and should not dominate the home screen.
