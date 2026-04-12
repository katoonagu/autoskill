from __future__ import annotations

from .models import AgentTask, ApprovalRecord, TaskSpawn
from .storage import (
    ControlPlanePaths,
    build_stable_approval_id,
    list_approvals,
    save_approval,
    utcnow_iso,
    write_json,
)


def create_approval_record(
    paths: ControlPlanePaths,
    *,
    scope: str,
    requested_by_agent: str,
    source_task: AgentTask,
    proposed_task: TaskSpawn,
    payload_ref: str,
    summary: str,
) -> ApprovalRecord:
    approval = ApprovalRecord(
        approval_id=build_stable_approval_id(scope, source_task.task_id, proposed_task.entity_refs),
        scope=scope,
        status="pending",
        created_at_iso=utcnow_iso(),
        requested_by_agent=requested_by_agent,
        task_id=source_task.task_id,
        entity_refs=dict(proposed_task.entity_refs),
        payload_ref=payload_ref,
        summary=summary,
        proposed_task=proposed_task.to_dict(),
    )
    save_approval(paths, approval, "pending")
    return approval


def resolve_approval(
    paths: ControlPlanePaths,
    *,
    approval_id: str,
    decision: str,
    actor: str,
    notes: str = "",
) -> ApprovalRecord:
    pending_records = {record.approval_id: (path, record) for path, record in list_approvals(paths, "pending")}
    if approval_id not in pending_records:
        raise RuntimeError(f"Pending approval not found: {approval_id}")
    path, approval = pending_records[approval_id]
    approval.status = decision
    approval.approved_by = actor
    approval.resolved_at_iso = utcnow_iso()
    approval.resolution_notes = notes
    path.unlink(missing_ok=True)
    save_approval(paths, approval, decision)
    return approval


def write_approval_index(paths: ControlPlanePaths):
    payload = {
        "pending": [record.to_dict() for _, record in list_approvals(paths, "pending")],
        "approved": [record.to_dict() for _, record in list_approvals(paths, "approved")],
        "rejected": [record.to_dict() for _, record in list_approvals(paths, "rejected")],
    }
    path = paths.output_root / "approvals_index.json"
    write_json(path, payload)
    return path
