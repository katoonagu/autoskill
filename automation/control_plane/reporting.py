from __future__ import annotations

from pathlib import Path
import json

from .storage import (
    APPROVAL_BUCKETS,
    TASK_BUCKETS,
    ControlPlanePaths,
    list_approvals,
    list_tasks,
    read_json,
    write_json,
)


def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _pair_key(brand_handle: str, blogger_handle: str) -> str:
    return f"{_slug(brand_handle)}__{_slug(blogger_handle or 'global')}"


def _recent_completed_items(paths: ControlPlanePaths, *, limit: int = 10) -> list[dict]:
    items: list[dict] = []
    for task_path, task in list_tasks(paths, "completed"):
        if str(task.task_id).startswith("manual_test_"):
            continue
        items.append(
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "assigned_agent": task.assigned_agent,
                "brand_handle": str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or ""),
                "blogger_handle": str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or ""),
                "updated_at_iso": task.updated_at_iso,
                "path": str(task_path),
            }
        )
    items.sort(key=lambda item: item["updated_at_iso"], reverse=True)
    return items[:limit]


def _codex_batches(paths: ControlPlanePaths, *, limit: int = 10) -> list[dict]:
    root = paths.output_root / "codex_review_batches"
    if not root.exists():
        return []
    batches: list[dict] = []
    completed_ids = {task.task_id for _, task in list_tasks(paths, "completed")}
    waiting_ids = {task.task_id for _, task in list_tasks(paths, "waiting_codex_review")}
    reviewing_ids = {task.task_id for _, task in list_tasks(paths, "codex_reviewing")}
    failed_ids = {task.task_id for _, task in list_tasks(paths, "failed")}

    for path in sorted(root.glob("*.json"), reverse=True):
        if path.name.startswith("manual_test_"):
            continue
        payload = _safe_read_json(path)
        tasks = payload.get("tasks") or []
        status_counts = {"completed": 0, "waiting_codex_review": 0, "codex_reviewing": 0, "failed": 0, "unknown": 0}
        for item in tasks:
            task_id = str(item.get("task_id") or "")
            if task_id in completed_ids:
                status_counts["completed"] += 1
            elif task_id in waiting_ids:
                status_counts["waiting_codex_review"] += 1
            elif task_id in reviewing_ids:
                status_counts["codex_reviewing"] += 1
            elif task_id in failed_ids:
                status_counts["failed"] += 1
            else:
                status_counts["unknown"] += 1
        batches.append(
            {
                "batch_id": str(payload.get("batch_id") or path.stem),
                "reviewer": str(payload.get("reviewer") or ""),
                "created_at_iso": str(payload.get("created_at_iso") or ""),
                "task_count": int(payload.get("task_count") or len(tasks)),
                "status_counts": status_counts,
                "manifest_path": str(path),
            }
        )
    return batches[:limit]


def _has_planning_material(paths: ControlPlanePaths, brand_handle: str, blogger_handle: str) -> bool:
    decision_path = paths.project_root / "output" / "outreach_planning" / _pair_key(brand_handle, blogger_handle) / "decision.json"
    return decision_path.exists()


def _collect_review_stage(paths: ControlPlanePaths, bucket: str) -> list[dict]:
    items: list[dict] = []
    for task_path, task in list_tasks(paths, bucket):
        if task.task_type != "brand_arbiter.evaluate_case" or str(task.task_id).startswith("manual_test_"):
            continue
        items.append(
            {
                "task_id": task.task_id,
                "brand_handle": str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or ""),
                "blogger_handle": str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or ""),
                "updated_at_iso": task.updated_at_iso,
                "blocked_reason": str(task.blocked_reason or ""),
                "evidence_bundle_path": str(task.inputs.get("evidence_bundle_path") or ""),
                "task_path": str(task_path),
            }
        )
    items.sort(key=lambda item: item["updated_at_iso"], reverse=True)
    return items


def _collect_ready_for_planning(paths: ControlPlanePaths) -> list[dict]:
    items: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for _, task in list_tasks(paths, "completed"):
        if task.task_type != "brand_arbiter.evaluate_case" or str(task.task_id).startswith("manual_test_"):
            continue
        if str(task.outputs.get("recommended_action") or "") != "plan_outreach":
            continue
        brand_handle = str(task.outputs.get("brand_handle") or task.entity_refs.get("brand_handle") or "")
        source_bloggers = [str(item).strip() for item in (task.outputs.get("source_bloggers") or []) if str(item).strip()]
        if not source_bloggers:
            fallback_blogger = str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or "").strip()
            if fallback_blogger:
                source_bloggers = [fallback_blogger]
        for blogger_handle in source_bloggers:
            pair = (brand_handle, blogger_handle)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if _has_planning_material(paths, brand_handle, blogger_handle):
                continue
            items.append(
                {
                    "brand_handle": brand_handle,
                    "blogger_handle": blogger_handle,
                    "intelligence_packet_path": str(task.outputs.get("intelligence_packet_path") or ""),
                    "arbiter_report_path": str(task.outputs.get("arbiter_report_path") or ""),
                    "updated_at_iso": task.updated_at_iso,
                }
            )

    items.sort(key=lambda item: item["updated_at_iso"], reverse=True)
    return items


def _collect_waiting_approval(paths: ControlPlanePaths) -> list[dict]:
    items: list[dict] = []
    for _, approval in list_approvals(paths, "pending"):
        items.append(
            {
                "approval_id": approval.approval_id,
                "scope": approval.scope,
                "brand_handle": str(approval.entity_refs.get("brand_handle") or ""),
                "blogger_handle": str(approval.entity_refs.get("blogger_handle") or ""),
                "payload_ref": approval.payload_ref,
                "created_at_iso": approval.created_at_iso,
            }
        )
    items.sort(key=lambda item: item["created_at_iso"], reverse=True)
    return items


def _collect_sent(paths: ControlPlanePaths) -> list[dict]:
    items: list[dict] = []
    for send_status_path in sorted((paths.project_root / "output" / "conversation").glob("**/send_status.json")):
        payload = _safe_read_json(send_status_path)
        if not payload:
            continue
        items.append(
            {
                "brand_handle": str(payload.get("brand_handle") or ""),
                "blogger_handle": str(payload.get("blogger_handle") or ""),
                "channel": str(payload.get("channel") or ""),
                "target_url": str(payload.get("target_url") or ""),
                "send_status_path": str(send_status_path),
                "updated_at_iso": send_status_path.stat().st_mtime,
            }
        )
    items.sort(key=lambda item: item["updated_at_iso"], reverse=True)
    return items


def build_status_report(paths: ControlPlanePaths) -> dict:
    task_counts = {bucket: len(list_tasks(paths, bucket)) for bucket in TASK_BUCKETS}
    approval_counts = {bucket: len(list_approvals(paths, bucket)) for bucket in APPROVAL_BUCKETS}
    run_summary = _safe_read_json(paths.output_root / "run_summary.json")
    approvals_index = _safe_read_json(paths.output_root / "approvals_index.json")
    return {
        "task_counts": task_counts,
        "approval_counts": approval_counts,
        "run_summary": run_summary,
        "recent_completed": _recent_completed_items(paths),
        "codex_batches": _codex_batches(paths),
        "pending_approvals": approvals_index.get("pending") or [],
    }


def build_codex_workboard(paths: ControlPlanePaths) -> dict:
    ready_for_review = _collect_review_stage(paths, "waiting_codex_review")
    in_review = _collect_review_stage(paths, "codex_reviewing")
    ready_for_planning = _collect_ready_for_planning(paths)
    waiting_approval = _collect_waiting_approval(paths)
    sent = _collect_sent(paths)
    return {
        "stage_counts": {
            "ready_for_review": len(ready_for_review),
            "in_review": len(in_review),
            "ready_for_planning": len(ready_for_planning),
            "waiting_approval": len(waiting_approval),
            "sent": len(sent),
        },
        "ready_for_review": ready_for_review,
        "in_review": in_review,
        "ready_for_planning": ready_for_planning,
        "waiting_approval": waiting_approval,
        "sent": sent,
    }


def write_status_report(paths: ControlPlanePaths) -> tuple[Path, Path]:
    payload = build_status_report(paths)
    json_path = paths.output_root / "status_report.json"
    md_path = paths.output_root / "status_report.md"
    write_json(json_path, payload)

    lines = [
        "# Supervisor Status",
        "",
        "## Task Buckets",
    ]
    for bucket, count in payload["task_counts"].items():
        lines.append(f"- {bucket}: {count}")

    lines.extend(["", "## Approvals"])
    for bucket, count in payload["approval_counts"].items():
        lines.append(f"- {bucket}: {count}")

    run_summary = payload.get("run_summary") or {}
    if run_summary:
        lines.extend(["", "## Last Run Summary"])
        for key in (
            "brain_mode",
            "seeded_tasks",
            "processed_tasks",
            "moved_to_codex_review",
            "waiting_codex_review",
            "created_downstream_tasks",
            "created_approvals",
            "failed_tasks",
            "pending_approvals",
        ):
            if key in run_summary:
                lines.append(f"- {key}: {run_summary[key]}")

    batches = payload.get("codex_batches") or []
    if batches:
        lines.extend(["", "## Codex Review Batches"])
        for batch in batches:
            counts = batch["status_counts"]
            lines.append(
                f"- {batch['batch_id']}: total={batch['task_count']}, "
                f"completed={counts['completed']}, waiting={counts['waiting_codex_review']}, "
                f"reviewing={counts['codex_reviewing']}, failed={counts['failed']}, unknown={counts['unknown']}"
            )

    pending_approvals = payload.get("pending_approvals") or []
    if pending_approvals:
        lines.extend(["", "## Pending Approvals"])
        for item in pending_approvals[:10]:
            lines.append(
                f"- {item.get('scope')}: @{item.get('entity_refs', {}).get('brand_handle', '')} "
                f"x @{item.get('entity_refs', {}).get('blogger_handle', '')} | {item.get('approval_id')}"
            )

    recent_completed = payload.get("recent_completed") or []
    if recent_completed:
        lines.extend(["", "## Recent Completed Tasks"])
        for item in recent_completed:
            lines.append(
                f"- {item['updated_at_iso']}: {item['task_type']} | "
                f"@{item['brand_handle'] or 'unknown'} @{item['blogger_handle'] or ''} | {item['task_id']}"
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return json_path, md_path


def write_codex_workboard(paths: ControlPlanePaths) -> tuple[Path, Path]:
    payload = build_codex_workboard(paths)
    json_path = paths.output_root / "codex_workboard.json"
    md_path = paths.output_root / "codex_workboard.md"
    write_json(json_path, payload)

    lines = [
        "# Codex Workboard",
        "",
        "## Stage Counts",
    ]
    for stage, count in payload["stage_counts"].items():
        lines.append(f"- {stage}: {count}")

    section_order = (
        ("ready_for_review", "Ready For Review"),
        ("in_review", "In Review"),
        ("ready_for_planning", "Ready For Planning"),
        ("waiting_approval", "Waiting Approval"),
        ("sent", "Sent"),
    )

    for key, title in section_order:
        lines.extend(["", f"## {title}"])
        items = payload.get(key) or []
        if not items:
            lines.append("- none")
            continue
        for item in items:
            brand_handle = item.get("brand_handle") or "unknown"
            blogger_handle = item.get("blogger_handle") or ""
            summary = f"@{brand_handle}"
            if blogger_handle:
                summary += f" x @{blogger_handle}"
            if key == "ready_for_review":
                extra = item.get("blocked_reason") or item.get("evidence_bundle_path") or item.get("task_id")
            elif key == "in_review":
                extra = item.get("task_id")
            elif key == "ready_for_planning":
                extra = item.get("intelligence_packet_path") or item.get("arbiter_report_path") or ""
            elif key == "waiting_approval":
                extra = f"{item.get('scope')} | {item.get('approval_id')}"
            else:
                extra = item.get("channel") or item.get("send_status_path") or ""
            lines.append(f"- {summary} | {extra}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return json_path, md_path


def write_reporting_bundle(paths: ControlPlanePaths) -> dict[str, str]:
    status_json, status_md = write_status_report(paths)
    workboard_json, workboard_md = write_codex_workboard(paths)
    return {
        "status_report_json": str(status_json),
        "status_report_md": str(status_md),
        "codex_workboard_json": str(workboard_json),
        "codex_workboard_md": str(workboard_md),
    }
