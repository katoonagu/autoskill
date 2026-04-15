from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.contracts import load_routing_rules, load_task_type_contracts
from automation.control_plane.reporting import write_reporting_bundle
from automation.control_plane.storage import ensure_control_plane_layout, list_tasks
from automation.control_plane.task_flow import finalize_success
from automation.modules.brand_arbiter.worker import persist_brand_arbiter_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize one manually reviewed Codex arbiter task.")
    parser.add_argument("--task-id", required=True, help="Task id from codex_reviewing.")
    parser.add_argument("--packet-path", required=True, help="Path to the reviewed intelligence packet JSON.")
    parser.add_argument("--report-path", default="", help="Optional path to a custom markdown arbiter report.")
    parser.add_argument("--skip-wiki", action="store_true", help="Skip writes into knowledge/llm_wiki.")
    return parser.parse_args()


def _load_task_from_codex_bucket(paths, task_id: str):
    for task_path, _task in list_tasks(paths, "codex_reviewing"):
        if _task.task_id == task_id:
            return task_path, _task
    raise RuntimeError(f"Task not found in codex_reviewing: {task_id}")


def main() -> None:
    args = parse_args()
    paths = ensure_control_plane_layout(PROJECT_ROOT)
    _, task = _load_task_from_codex_bucket(paths, args.task_id)

    packet_path = Path(args.packet_path)
    if not packet_path.exists():
        raise RuntimeError(f"Packet JSON not found: {packet_path}")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))

    report_markdown = ""
    if args.report_path:
        report_path = Path(args.report_path)
        if not report_path.exists():
            raise RuntimeError(f"Report markdown not found: {report_path}")
        report_markdown = report_path.read_text(encoding="utf-8")

    evidence_bundle_path = Path(str(task.inputs.get("evidence_bundle_path") or ""))
    if not evidence_bundle_path.exists():
        raise RuntimeError(f"Evidence bundle not found: {evidence_bundle_path}")
    evidence_bundle = json.loads(evidence_bundle_path.read_text(encoding="utf-8"))

    media_report = None
    media_report_path = str(task.inputs.get("media_report_path") or "")
    if media_report_path:
        media_path = Path(media_report_path)
        if media_path.exists():
            media_report = json.loads(media_path.read_text(encoding="utf-8"))

    packet["llm_provider"] = str(packet.get("llm_provider") or "codex_manual_review")
    result = persist_brand_arbiter_result(
        PROJECT_ROOT,
        task,
        evidence_bundle=evidence_bundle,
        packet=packet,
        media_report=media_report,
        write_wiki=not args.skip_wiki,
        custom_report_markdown=report_markdown,
    )

    routing_rules = load_routing_rules(PROJECT_ROOT)
    task_contracts = load_task_type_contracts(PROJECT_ROOT)
    created_count, approval_count = finalize_success(PROJECT_ROOT, paths, task, result, routing_rules, task_contracts)
    write_reporting_bundle(paths)
    print(
        json.dumps(
            {
                "task_id": task.task_id,
                "brand_handle": result.outputs.get("brand_handle"),
                "verdict": result.outputs.get("verdict"),
                "recommended_action": result.outputs.get("recommended_action"),
                "created_downstream_tasks": created_count,
                "created_approvals": approval_count,
                "intelligence_packet_path": result.outputs.get("intelligence_packet_path"),
                "arbiter_report_path": result.outputs.get("arbiter_report_path"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


