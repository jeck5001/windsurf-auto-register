# Account Password List Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show stored account passwords directly in the Accounts table.

**Architecture:** Use the existing repository data flow: `Repository.list_accounts()` already returns `password`, `routes_pages.py` already passes accounts to the template, and `webapp/templates/accounts.html` only needs an extra column. Validate behavior through the existing FastAPI page-rendering test.

**Tech Stack:** FastAPI, Jinja2 templates, pytest, SQLite-backed repository.

---

### Task 1: Render Passwords In Accounts Table

**Files:**
- Modify: `tests/test_pages.py`
- Modify: `webapp/templates/accounts.html`

- [ ] **Step 1: Write the failing test**

In `tests/test_pages.py`, update `test_accounts_and_settings_pages_show_live_data` so the saved result includes a password and the response must include both the header and value:

```python
        result={
            "email": "account@example.com",
            "password": "StoredPass123",
            "ott": "ott$masked",
            "trial_checkout_url": trial_url,
            "pool_result": {"account": {"status": "active"}},
        },
```

Add these assertions after the email assertion:

```python
    assert "Password" in accounts_response.text
    assert "StoredPass123" in accounts_response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_pages.py::test_accounts_and_settings_pages_show_live_data -q
```

Expected: FAIL because `StoredPass123` is not rendered in the Accounts table.

- [ ] **Step 3: Write minimal implementation**

In `webapp/templates/accounts.html`, add a password header after the email header:

```html
        <th>{{ t("accounts.password") }}</th>
```

Add a password cell after the email cell:

```html
        <td>
          {% if account.password %}
          {{ account.password }}
          {% else %}
          <span class="muted">-</span>
          {% endif %}
        </td>
```

Change the empty row from:

```html
      <tr><td colspan="5">{{ t("accounts.empty") }}</td></tr>
```

to:

```html
      <tr><td colspan="6">{{ t("accounts.empty") }}</td></tr>
```

- [ ] **Step 4: Run focused test to verify it passes**

Run:

```bash
pytest tests/test_pages.py::test_accounts_and_settings_pages_show_live_data -q
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

Run:

```bash
pytest -q
```

Expected: PASS.
