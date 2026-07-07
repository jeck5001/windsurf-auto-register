from __future__ import annotations

from typing import Any


def sync_pool_accounts(repo, pool_client) -> int:
    accounts = pool_client.list_accounts()
    imported = 0
    for account in accounts:
        if not isinstance(account, dict):
            continue
        email = str(account.get("email") or "").strip()
        if not email:
            continue
        repo.upsert_pool_account(
            email=email,
            password=str(account.get("password") or "").strip(),
            pool_status=str(account.get("status") or "").strip(),
        )
        imported += 1
    return imported
