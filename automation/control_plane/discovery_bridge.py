from __future__ import annotations

from pathlib import Path

import yaml

from ..modules.instagram_brand_search.recipe import collect_exportable_brand_records
from ..modules.instagram_brand_search.state import InstagramBrandSearchState
from .contracts import load_task_type_contracts
from .models import AgentTask
from .storage import ControlPlanePaths, build_stable_task_id, save_task, task_exists, utcnow_iso, write_json


def _load_discovery_job(project_root: Path) -> dict:
    path = project_root / "automation" / "modules" / "instagram_brand_search" / "job.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    payload["state"]["state_file"] = str(project_root / payload["state"]["state_file"])
    return payload


def _snapshot_path(paths: ControlPlanePaths, handle: str) -> Path:
    return paths.normalized_root / "discovery_brand_snapshots" / f"{handle}.json"


def seed_brand_intelligence_tasks(project_root: Path, paths: ControlPlanePaths) -> list[AgentTask]:
    contracts = load_task_type_contracts(project_root)
    contract = contracts["brand_intelligence.evaluate_brand"]
    discovery_job = _load_discovery_job(project_root)
    discovery_state = InstagramBrandSearchState.load(Path(discovery_job["state"]["state_file"]))
    exportable_records = collect_exportable_brand_records(discovery_state)

    created: list[AgentTask] = []
    summary_rows: list[dict] = []
    for handle, record in exportable_records:
        snapshot = dict(record)
        snapshot["handle"] = handle
        snapshot_path = _snapshot_path(paths, handle)
        write_json(snapshot_path, snapshot)

        source_bloggers = sorted(
            {
                str(source.get("blogger_handle", "")).strip().lstrip("@")
                for source in (record.get("sources") or [])
                if str(source.get("blogger_handle", "")).strip()
            }
        )
        entity_refs = {"brand_handle": handle}
        task = AgentTask(
            task_id=build_stable_task_id(contract.task_type, entity_refs),
            task_type=contract.task_type,
            assigned_agent=contract.assigned_agent,
            status="pending",
            priority="normal",
            created_at_iso=utcnow_iso(),
            updated_at_iso=utcnow_iso(),
            source_run_id="discovery_state_bridge",
            entity_refs=entity_refs,
            inputs={
                "brand_snapshot_path": str(snapshot_path),
                "source_bloggers": source_bloggers,
                "source_posts_count": len(record.get("sources", []) or []),
            },
            evidence_refs=[str(snapshot_path)],
            max_attempts=contract.max_attempts,
            requires_browser=contract.requires_browser,
            required_profile_capability=contract.required_profile_capability,
            requires_human_approval=contract.requires_human_approval,
            approval_scope=contract.approval_scope,
        )
        if not task_exists(paths, task.task_id):
            save_task(paths, task, "inbox")
            created.append(task)
        summary_rows.append(
            {
                "brand_handle": handle,
                "snapshot_path": str(snapshot_path),
                "source_bloggers": source_bloggers,
                "task_id": task.task_id,
            }
        )

    write_json(
        paths.output_root / "discovery_seed_summary.json",
        {
            "seeded_at_iso": utcnow_iso(),
            "exportable_brand_records": len(exportable_records),
            "created_tasks": len(created),
            "brands": summary_rows,
        },
    )
    return created
