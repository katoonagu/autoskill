from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import json

from .models import AgentTask, ApprovalRecord, TaskResult


TASK_BUCKETS = ("inbox", "processing", "blocked", "completed", "failed")
APPROVAL_BUCKETS = ("pending", "approved", "rejected", "expired")


@dataclass(frozen=True)
class ControlPlanePaths:
    project_root: Path
    tasks_root: Path
    decisions_root: Path
    state_root: Path
    output_root: Path
    normalized_root: Path
    results_root: Path
    route_logs_root: Path


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_control_plane_layout(project_root: Path) -> ControlPlanePaths:
    tasks_root = project_root / "automation" / "tasks"
    decisions_root = project_root / "automation" / "decisions"
    state_root = project_root / "automation" / "state"
    output_root = project_root / "output" / "supervisor"
    normalized_root = output_root / "normalized"
    results_root = output_root / "results"
    route_logs_root = output_root / "routing"

    for bucket in TASK_BUCKETS:
        (tasks_root / bucket).mkdir(parents=True, exist_ok=True)
    for bucket in APPROVAL_BUCKETS:
        (decisions_root / bucket).mkdir(parents=True, exist_ok=True)
    for directory in (
        state_root / "agents",
        state_root / "leases",
        state_root / "runs",
        normalized_root,
        results_root,
        route_logs_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return ControlPlanePaths(
        project_root=project_root,
        tasks_root=tasks_root,
        decisions_root=decisions_root,
        state_root=state_root,
        output_root=output_root,
        normalized_root=normalized_root,
        results_root=results_root,
        route_logs_root=route_logs_root,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def task_storage_path(paths: ControlPlanePaths, bucket: str, task: AgentTask) -> Path:
    return paths.tasks_root / bucket / task.assigned_agent / f"{task.task_id}.json"


def approval_storage_path(paths: ControlPlanePaths, bucket: str, approval: ApprovalRecord) -> Path:
    return paths.decisions_root / bucket / f"{approval.approval_id}.json"


def save_task(paths: ControlPlanePaths, task: AgentTask, bucket: str) -> Path:
    path = task_storage_path(paths, bucket, task)
    write_json(path, task.to_dict())
    return path


def remove_task(paths: ControlPlanePaths, task_id: str) -> None:
    for bucket in TASK_BUCKETS:
        for path in (paths.tasks_root / bucket).rglob(f"{task_id}.json"):
            path.unlink(missing_ok=True)


def load_task(path: Path) -> AgentTask:
    return AgentTask.from_dict(read_json(path))


def list_tasks(paths: ControlPlanePaths, bucket: str) -> list[tuple[Path, AgentTask]]:
    root = paths.tasks_root / bucket
    if not root.exists():
        return []
    items: list[tuple[Path, AgentTask]] = []
    for path in sorted(root.rglob("*.json")):
        items.append((path, load_task(path)))
    return items


def task_exists(paths: ControlPlanePaths, task_id: str) -> bool:
    for bucket in TASK_BUCKETS:
        for path in (paths.tasks_root / bucket).rglob(f"{task_id}.json"):
            if path.exists():
                return True
    return False


def save_result(paths: ControlPlanePaths, result: TaskResult) -> Path:
    path = paths.results_root / f"{result.task_id}.json"
    write_json(path, result.to_dict())
    return path


def result_exists(paths: ControlPlanePaths, task_id: str) -> bool:
    return (paths.results_root / f"{task_id}.json").exists()


def save_approval(paths: ControlPlanePaths, approval: ApprovalRecord, bucket: str) -> Path:
    path = approval_storage_path(paths, bucket, approval)
    write_json(path, approval.to_dict())
    return path


def load_approval(path: Path) -> ApprovalRecord:
    return ApprovalRecord.from_dict(read_json(path))


def list_approvals(paths: ControlPlanePaths, bucket: str) -> list[tuple[Path, ApprovalRecord]]:
    root = paths.decisions_root / bucket
    if not root.exists():
        return []
    items: list[tuple[Path, ApprovalRecord]] = []
    for path in sorted(root.glob("*.json")):
        items.append((path, load_approval(path)))
    return items


def build_stable_task_id(task_type: str, entity_refs: dict[str, str]) -> str:
    canonical = json.dumps(
        {"task_type": task_type, "entity_refs": entity_refs},
        ensure_ascii=False,
        sort_keys=True,
    )
    return f"{task_type.replace('.', '__')}__{sha1(canonical.encode('utf-8')).hexdigest()[:12]}"


def build_stable_approval_id(scope: str, task_id: str, entity_refs: dict[str, str]) -> str:
    canonical = json.dumps(
        {"scope": scope, "task_id": task_id, "entity_refs": entity_refs},
        ensure_ascii=False,
        sort_keys=True,
    )
    return f"{scope.replace('.', '__')}__{sha1(canonical.encode('utf-8')).hexdigest()[:12]}"
