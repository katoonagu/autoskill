from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from automation.paths import artifacts_root, resolve_repo_path

from .models import ActionRun, LaunchAction
from .utils import safe_read_json, utcnow_iso


def action_runs_path(project_root: Path) -> Path:
    return artifacts_root(project_root) / "agent_canvas" / "action_runs.json"


def _actions_log_dir(project_root: Path) -> Path:
    return artifacts_root(project_root) / "agent_canvas" / "actions"


def get_launch_actions(project_root: Path) -> list[LaunchAction]:
    python = sys.executable
    return [
        LaunchAction(
            id="run_supervisor",
            label="Run Supervisor",
            description="Execute the multi-agent control plane with default max-tasks.",
            command=[python, "scripts/run_supervisor.py", "--max-tasks", "25"],
            group="control_plane",
        ),
        LaunchAction(
            id="run_theblueprint_parser",
            label="Run Blueprint Parser",
            description="Refresh the full The Blueprint career archive and shortlist.",
            command=[
                python,
                "scripts/run_theblueprint_career_parser.py",
                "--mode",
                "brand-pages",
                "--max-workers",
                "10",
                "--refresh-shortlist",
            ],
            group="company_contacts_enrichment",
        ),
        LaunchAction(
            id="rebuild_theblueprint_shortlist",
            label="Rebuild Blueprint Shortlist",
            description="Regenerate the outreach shortlist from the archive output.",
            command=[python, "scripts/admin/rebuild_theblueprint_career_hiring.py"],
            group="company_contacts_enrichment",
        ),
        LaunchAction(
            id="build_theblueprint_people_targets",
            label="Build People Targets",
            description="Rebuild the stage-2 people targets shortlist.",
            command=[python, "scripts/build_theblueprint_people_targets.py"],
            group="company_contacts_enrichment",
        ),
        LaunchAction(
            id="build_theblueprint_master_report",
            label="Build Master Report",
            description="Regenerate the master company contacts report bundle.",
            command=[python, "scripts/build_theblueprint_master_report.py"],
            group="company_contacts_enrichment",
        ),
        LaunchAction(
            id="audit_instagram_dm_targets",
            label="Audit Instagram DM Targets",
            description="Read the DM target list and refresh outbound DM status snapshots.",
            command=[python, "scripts/reporting/audit_instagram_dm_targets.py"],
            group="outreach_execution",
        ),
    ]


class ActionRegistry:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def list_actions(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in get_launch_actions(self.project_root)]

    def _load_runs(self) -> list[dict[str, Any]]:
        payload = safe_read_json(action_runs_path(self.project_root))
        runs = payload.get("runs") or []
        return runs if isinstance(runs, list) else []

    def _write_runs(self, runs: list[dict[str, Any]]) -> None:
        path = action_runs_path(self.project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            __import__("json").dumps({"runs": runs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def refresh_runs(self) -> list[dict[str, Any]]:
        runs = self._load_runs()
        changed = False
        for item in runs:
            if item.get("status") != "running":
                continue
            run_id = str(item.get("run_id") or "")
            process = self._processes.get(run_id)
            if process is None:
                continue
            exit_code = process.poll()
            if exit_code is None:
                continue
            item["exit_code"] = int(exit_code)
            item["finished_at"] = utcnow_iso()
            item["status"] = "completed" if exit_code == 0 else "failed"
            self._processes.pop(run_id, None)
            changed = True
        if changed:
            self._write_runs(runs)
        return runs

    def start_action(self, action_id: str) -> dict[str, Any]:
        actions = {item.id: item for item in get_launch_actions(self.project_root)}
        if action_id not in actions:
            raise KeyError(action_id)
        action = actions[action_id]

        run_id = f"{action.id}__{utcnow_iso().replace(':', '').replace('-', '')}"
        log_dir = _actions_log_dir(self.project_root)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{run_id}.log"

        handle = log_path.open("w", encoding="utf-8")
        command = [str(resolve_repo_path(self.project_root, part)) if part.endswith(".py") else part for part in action.command]
        process = subprocess.Popen(
            command,
            cwd=self.project_root,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._processes[run_id] = process

        run = ActionRun(
            run_id=run_id,
            action_id=action.id,
            label=action.label,
            status="running",
            started_at=utcnow_iso(),
            log_path=str(log_path.relative_to(self.project_root).as_posix()),
            pid=process.pid,
        )
        runs = self._load_runs()
        runs.insert(0, run.to_dict())
        self._write_runs(runs)
        return run.to_dict()
