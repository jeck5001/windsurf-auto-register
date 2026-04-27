from __future__ import annotations

from pathlib import Path

from windsurf_auth_replay import load_dotenv


def _candidate_env_paths(start: Path) -> list[Path]:
    roots = [start, *start.parents]
    candidates: list[Path] = []

    worktrees_index = next((index for index, root in enumerate(roots) if root.name == ".worktrees"), None)
    if worktrees_index is not None and worktrees_index + 1 < len(roots):
        candidates.append(roots[worktrees_index + 1] / ".env")

    for root in roots:
        candidates.append(root / ".env")
    return candidates


def load_project_env(start: Path | None = None) -> None:
    search_root = (start or Path.cwd()).resolve()
    seen: set[Path] = set()
    for path in _candidate_env_paths(search_root):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            load_dotenv(str(resolved))
