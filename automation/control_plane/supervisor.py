from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from .approvals import write_approval_index
from .contracts import load_profile_pool, load_routing_rules, load_task_type_contracts
from .discovery_bridge import seed_brand_intelligence_tasks
from .models import AgentTask, TaskResult, TaskSpawn
from .profiles import acquire_profile_lease, release_profile_lease
from .reporting import write_reporting_bundle
from .storage import (
    ControlPlanePaths,
    ensure_control_plane_layout,
    list_approvals,
    list_tasks,
    save_task,
    utcnow_iso,
    write_json,
    remove_task,
)
from .task_flow import finalize_success, materialize_spawn


@dataclass(frozen=True)
class SupervisorOptions:
    max_tasks: int = 25
    seed_from_discovery: bool = True
    seed_only: bool = False
    write_wiki: bool = True
    allowed_agents: tuple[str, ...] = ()
    brain_mode: str = ""


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _resolve_brain_mode(project_root: Path, override: str) -> str:
    if override.strip():
        return override.strip().lower()
    env_values: dict[str, str] = {}
    env_values.update(_read_env_file(project_root / ".env"))
    env_values.update(_read_env_file(project_root / ".env.local"))
    return (
        os.environ.get("AUTOSKILL_BRAIN_MODE")
        or env_values.get("AUTOSKILL_BRAIN_MODE")
        or "api"
    ).strip().lower()


def _dispatch_task(project_root: Path, task: AgentTask, *, write_wiki: bool) -> TaskResult:
    if task.assigned_agent == "brand_intelligence_agent":
        from ..modules.brand_intelligence.worker import run_brand_intelligence_task

        return run_brand_intelligence_task(project_root, task, write_wiki=write_wiki)
    if task.assigned_agent == "brand_arbiter_agent":
        from ..modules.brand_arbiter.worker import run_brand_arbiter_task

        return run_brand_arbiter_task(project_root, task, write_wiki=write_wiki)
    if task.assigned_agent == "media_intelligence_agent":
        from ..modules.media_intelligence.worker import run_media_intelligence_task

        return run_media_intelligence_task(project_root, task, write_wiki=write_wiki)
    if task.assigned_agent == "outreach_planning_agent":
        from ..modules.outreach_planning.worker import run_outreach_planning_task

        return run_outreach_planning_task(project_root, task, write_wiki=write_wiki)
    if task.assigned_agent == "conversation_agent":
        from ..modules.conversation.worker import run_conversation_task

        return run_conversation_task(project_root, task, write_wiki=write_wiki)
    if task.assigned_agent == "feedback_validation_agent":
        from ..modules.feedback_validation.worker import run_validation_task

        return run_validation_task(project_root, task, write_wiki=write_wiki)
    raise RuntimeError(f"No worker registered for agent {task.assigned_agent}")


def _promote_approved_tasks(project_root: Path, paths: ControlPlanePaths, task_contracts) -> int:
    promoted = 0
    for _path, approval in list_approvals(paths, "approved"):
        spawn = TaskSpawn(**approval.proposed_task)
        task = materialize_spawn(project_root, paths, spawn, task_contracts)
        if task is not None:
            promoted += 1
    return promoted


def _write_run_summary(paths: ControlPlanePaths, summary: dict):
    path = paths.output_root / "run_summary.json"
    write_json(path, summary)
    return path


def _load_supporting_stats_for_task(task: AgentTask) -> dict:
    stats = dict(task.inputs.get("supporting_stats") or {})
    evidence_bundle_path = str(task.inputs.get("evidence_bundle_path") or "")
    if stats or not evidence_bundle_path:
        return stats
    bundle_path = Path(evidence_bundle_path)
    if not bundle_path.exists():
        return {}
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload.get("mention_statistics") or {})


def _should_route_task_to_codex(task: AgentTask, *, brain_mode: str) -> tuple[bool, str]:
    if task.task_type != "brand_arbiter.evaluate_case":
        return False, ""
    normalized_mode = brain_mode.strip().lower()
    if normalized_mode == "codex":
        return True, "Brain mode is codex."
    if normalized_mode != "hybrid":
        return False, ""

    stats = _load_supporting_stats_for_task(task)
    reasons: list[str] = []
    if str(stats.get("brand_value_tier") or "").strip().lower() == "high":
        reasons.append("high_value_brand")
    if bool(stats.get("signal_conflict")):
        reasons.append("signal_conflict")
    if bool(stats.get("personalization_gap")):
        reasons.append("personalization_gap")
    if int(stats.get("unique_blogger_count") or 0) < 2:
        reasons.append("limited_creator_context")
    if not bool(stats.get("official_site_found")) and int(stats.get("review_source_count") or 0) == 0:
        reasons.append("weak_external_evidence")
    if task.inputs.get("force_codex_review"):
        reasons.append("force_codex_review")
    if not reasons:
        return False, ""
    return True, ", ".join(reasons)


def run_supervisor(project_root: Path, options: SupervisorOptions | None = None) -> dict:
    options = options or SupervisorOptions()
    paths = ensure_control_plane_layout(project_root)
    task_contracts = load_task_type_contracts(project_root)
    routing_rules = load_routing_rules(project_root)
    profile_pool = load_profile_pool(project_root)
    brain_mode = _resolve_brain_mode(project_root, options.brain_mode)

    seeded_count = 0
    if options.seed_from_discovery:
        seeded_count = len(seed_brand_intelligence_tasks(project_root, paths))

    promoted_count = _promote_approved_tasks(project_root, paths, task_contracts)

    processed_count = 0
    created_count = 0
    approval_count = 0
    failed_count = 0
    codex_review_count = 0
    processed_task_ids: list[str] = []

    if not options.seed_only and options.max_tasks > 0:
        for task_path, task in list_tasks(paths, "inbox"):
            if options.allowed_agents and task.assigned_agent not in options.allowed_agents:
                continue
            if processed_count >= options.max_tasks:
                break

            lease_profile_key = ""
            try:
                route_to_codex, codex_reason = _should_route_task_to_codex(task, brain_mode=brain_mode)
                if route_to_codex:
                    task.status = "waiting_codex_review"
                    task.blocked_reason = codex_reason
                    task.updated_at_iso = utcnow_iso()
                    task_path.unlink(missing_ok=True)
                    save_task(paths, task, "waiting_codex_review")
                    codex_review_count += 1
                    continue

                if task.requires_browser and task.required_profile_capability:
                    lease = acquire_profile_lease(
                        paths,
                        pool=profile_pool,
                        capability=task.required_profile_capability,
                        task_id=task.task_id,
                        agent=task.assigned_agent,
                    )
                    if lease is None:
                        task.status = "blocked"
                        task.blocked_reason = f"No free profile for capability {task.required_profile_capability}"
                        task.updated_at_iso = utcnow_iso()
                        task_path.unlink(missing_ok=True)
                        save_task(paths, task, "blocked")
                        continue
                    lease_profile_key = lease.profile_key
                    task.inputs["_leased_profile_no"] = lease.profile_no
                    task.inputs["_leased_profile_key"] = lease.profile_key

                task.status = "running"
                task.updated_at_iso = utcnow_iso()
                task_path.unlink(missing_ok=True)
                save_task(paths, task, "processing")
                result = _dispatch_task(project_root, task, write_wiki=options.write_wiki)

                remove_task(paths, task.task_id)
                task.status = "completed"
                task.updated_at_iso = result.completed_at_iso
                task.outputs = dict(result.outputs)
                task.evidence_refs = list(result.evidence_refs)
                processed_task_ids.append(task.task_id)
                processed_count += 1
                new_tasks, new_approvals = finalize_success(project_root, paths, task, result, routing_rules, task_contracts)
                created_count += new_tasks
                approval_count += new_approvals
            except Exception as exc:
                remove_task(paths, task.task_id)
                task.attempts += 1
                task.updated_at_iso = utcnow_iso()
                task.blocked_reason = str(exc)
                task.status = "failed_retryable" if task.attempts < task.max_attempts else "failed_terminal"
                save_task(paths, task, "inbox" if task.status == "failed_retryable" else "failed")
                failed_count += 1
            finally:
                if lease_profile_key:
                    release_profile_lease(paths, profile_key=lease_profile_key)

    approvals_index = write_approval_index(paths)
    summary = {
        "seeded_tasks": seeded_count,
        "promoted_approved_tasks": promoted_count,
        "processed_tasks": processed_count,
        "brain_mode": brain_mode,
        "waiting_codex_review": len(list_tasks(paths, "waiting_codex_review")),
        "moved_to_codex_review": codex_review_count,
        "created_downstream_tasks": created_count,
        "created_approvals": approval_count,
        "failed_tasks": failed_count,
        "processed_task_ids": processed_task_ids,
        "pending_approvals": len(list_approvals(paths, "pending")),
        "approvals_index": str(approvals_index),
    }
    _write_run_summary(paths, summary)
    write_reporting_bundle(paths)
    return summary
