from __future__ import annotations

from pathlib import Path

RUNTIME_DIRNAME = "runtime"
ARTIFACTS_DIRNAME = "artifacts"

_LEGACY_PREFIXES = (
    ("automation/state", "runtime/state"),
    ("automation/tasks", "runtime/tasks"),
    ("automation/decisions", "runtime/decisions"),
    ("output", "artifacts"),
)


def runtime_root(project_root: Path) -> Path:
    return project_root / RUNTIME_DIRNAME


def artifacts_root(project_root: Path) -> Path:
    return project_root / ARTIFACTS_DIRNAME


def runtime_state_root(project_root: Path) -> Path:
    return runtime_root(project_root) / "state"


def runtime_tasks_root(project_root: Path) -> Path:
    return runtime_root(project_root) / "tasks"


def runtime_decisions_root(project_root: Path) -> Path:
    return runtime_root(project_root) / "decisions"


def resolve_repo_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    normalized = str(raw_path).replace("\\", "/").strip()
    for legacy_prefix, new_prefix in _LEGACY_PREFIXES:
        if normalized == legacy_prefix:
            normalized = new_prefix
            break
        if normalized.startswith(f"{legacy_prefix}/"):
            suffix = normalized[len(legacy_prefix) + 1 :]
            normalized = f"{new_prefix}/{suffix}"
            break
    return project_root / Path(normalized)


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    while current.parent != current:
        if (current / "automation").exists():
            return current
        current = current.parent
    raise RuntimeError(f"Project root not found from {start}")


def ensure_runtime_layout(project_root: Path) -> None:
    for directory in (
        runtime_state_root(project_root),
        runtime_state_root(project_root) / "agents",
        runtime_state_root(project_root) / "leases",
        runtime_state_root(project_root) / "runs",
        runtime_state_root(project_root) / "subagents",
        runtime_tasks_root(project_root),
        runtime_decisions_root(project_root),
    ):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_artifacts_layout(project_root: Path) -> None:
    for directory in (
        artifacts_root(project_root),
        artifacts_root(project_root) / "playwright",
        artifacts_root(project_root) / "supervisor",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_project_layout(project_root: Path) -> None:
    ensure_runtime_layout(project_root)
    ensure_artifacts_layout(project_root)
