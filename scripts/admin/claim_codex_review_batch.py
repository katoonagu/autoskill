from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.storage import ensure_control_plane_layout, list_tasks, save_task, utcnow_iso
from automation.control_plane.reporting import write_reporting_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claim a batch of Codex-review tasks for manual arbiter work.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of tasks to claim.")
    parser.add_argument("--agent", default="brand_arbiter_agent", help="Assigned agent filter.")
    parser.add_argument("--reviewer", default="codex", help="Reviewer label stored in the batch manifest.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ensure_control_plane_layout(PROJECT_ROOT)
    batch_id = f"codex_batch_{utcnow_iso().replace(':', '').replace('-', '').replace('.', '')}_{uuid4().hex[:6]}"
    claimed: list[dict] = []

    for task_path, task in list_tasks(paths, "waiting_codex_review"):
        if args.agent and task.assigned_agent != args.agent:
            continue
        if len(claimed) >= max(args.limit, 0):
            break
        task_path.unlink(missing_ok=True)
        task.status = "codex_reviewing"
        task.updated_at_iso = utcnow_iso()
        save_task(paths, task, "codex_reviewing")
        claimed.append(
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "assigned_agent": task.assigned_agent,
                "brand_handle": str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or ""),
                "blogger_handle": str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or ""),
                "reason": str(task.blocked_reason or ""),
                "evidence_bundle_path": str(task.inputs.get("evidence_bundle_path") or ""),
                "evidence_report_path": str(task.inputs.get("evidence_report_path") or ""),
                "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
                "media_report_path": str(task.inputs.get("media_report_path") or ""),
            }
        )

    manifest = {
        "batch_id": batch_id,
        "reviewer": args.reviewer,
        "created_at_iso": utcnow_iso(),
        "task_count": len(claimed),
        "tasks": claimed,
    }
    manifest_path = paths.output_root / "codex_review_batches" / f"{batch_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reporting_bundle(paths)
    print(json.dumps({"batch_id": batch_id, "manifest_path": str(manifest_path), "task_count": len(claimed)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


