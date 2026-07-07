# Account Password List Display Design

## Goal

Show each stored account password directly on the web Accounts page so operators can quickly recover or copy credentials without opening the edit dialog.

## Current State

The admin UI stores account passwords in the `accounts.password` SQLite column and returns that field through `Repository.list_accounts()`. The Accounts page already has localized `accounts.password` labels and an edit modal field for the password, but the table only renders email, mode, pool status, trial URL, and actions.

## Design

Add a `Password` column to the Accounts table between `Email` and `Mode`. Render `account.password` as plain text when present and render the existing muted dash placeholder when empty. Keep the edit modal unchanged because it already exposes the password for editing.

The empty-table row should span six columns after the new column is added. Existing English and Chinese translations need no changes because `accounts.password` already exists in `webapp/i18n.py`.

## Testing

Update the page rendering test to save an account result with a password and assert that the Accounts page response includes the `Password` header and stored password value. Run the focused page test first, then the full test suite.
