from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.storage import ensure_control_plane_layout, list_tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List pending tasks in the Codex review queue.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of queue items to print.")
    parser.add_argument(
        "--bucket",
        choices=("waiting_codex_review", "codex_reviewing"),
        default="waiting_codex_review",
        help="Which Codex-review bucket to inspect.",
    )
    parser.add_argument(
        "--agent",
        default="brand_arbiter_agent",
        help="Optional assigned_agent filter. Defaults to brand_arbiter_agent.",
    )
    parser.add_argument("--json", action="store_true", help="Print queue items as JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ensure_control_plane_layout(PROJECT_ROOT)
    items = []
    for _path, task in list_tasks(paths, args.bucket):
        if args.agent and task.assigned_agent != args.agent:
            continue
        items.append(
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
                "updated_at_iso": task.updated_at_iso,
            }
        )

    items = items[: max(args.limit, 0)]
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    for index, item in enumerate(items, start=1):
        print(f"{index}. {item['brand_handle'] or 'unknown'} | {item['task_id']}")
        print(f"   agent: {item['assigned_agent']}")
        print(f"   reason: {item['reason'] or 'n/a'}")
        print(f"   evidence: {item['evidence_bundle_path'] or 'n/a'}")
        if item["media_report_path"]:
            print(f"   media: {item['media_report_path']}")
        print("")


if __name__ == "__main__":
    main()
