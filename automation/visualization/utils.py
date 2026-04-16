from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from automation.paths import resolve_repo_path

from .models import GraphLink

STATUS_PRIORITY = (
    "running",
    "waiting_review",
    "waiting_approval",
    "blocked",
    "failed",
    "partial",
    "queued",
    "completed",
    "idle",
)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return ""


def path_mtime_iso(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def latest_iso(values: list[str]) -> str:
    ordered = [item for item in values if item]
    if not ordered:
        return ""
    return max(ordered)


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "idle"
    lookup = {status: index for index, status in enumerate(STATUS_PRIORITY)}
    return min(statuses, key=lambda item: lookup.get(item, len(STATUS_PRIORITY)))


def derive_status(
    *,
    running: int = 0,
    queued: int = 0,
    completed: int = 0,
    waiting_review: int = 0,
    waiting_approval: int = 0,
    blocked: int = 0,
    failed: int = 0,
) -> str:
    if running:
        return "running"
    if waiting_review:
        return "waiting_review"
    if waiting_approval:
        return "waiting_approval"
    if blocked:
        return "blocked"
    if failed and not completed:
        return "failed"
    if completed and (queued or failed or waiting_review or waiting_approval):
        return "partial"
    if completed:
        return "completed"
    if queued:
        return "queued"
    if failed:
        return "failed"
    return "idle"


def compact_counts(raw: dict[str, int]) -> dict[str, int]:
    return {key: value for key, value in raw.items() if int(value or 0) > 0}


def progress_text_from_counts(counts: dict[str, int], ordered_keys: list[str]) -> str:
    parts: list[str] = []
    for key in ordered_keys:
        value = int(counts.get(key) or 0)
        if value <= 0:
            continue
        parts.append(f"{value} {key.replace('_', ' ')}")
    return ", ".join(parts) if parts else "No recent activity"


def rel_path(project_root: Path, raw_path: str | Path) -> str:
    path = resolve_repo_path(project_root, raw_path)
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return str(path)


def make_link(project_root: Path, label: str, raw_path: str | Path, *, kind: str = "file") -> GraphLink:
    return GraphLink(label=label, path=rel_path(project_root, raw_path), kind=kind)


def file_count(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.glob(pattern))


def list_recent_files(root: Path, pattern: str, *, limit: int = 5) -> list[Path]:
    if not root.exists():
        return []
    items = sorted(root.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return items[:limit]


def append_markdown_section(lines: list[str], title: str, body_lines: list[str]) -> None:
    if not body_lines:
        return
    lines.extend(["", f"## {title}", ""])
    lines.extend(body_lines)
