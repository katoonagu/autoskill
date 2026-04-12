from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .approvals import create_approval_record, write_approval_index
from .contracts import load_profile_pool, load_routing_rules, load_task_type_contracts
from .discovery_bridge import seed_brand_intelligence_tasks
from .models import AgentTask, RouteRule, TaskResult, TaskSpawn
from .profiles import acquire_profile_lease, release_profile_lease
from .storage import (
    ControlPlanePaths,
    build_stable_task_id,
    ensure_control_plane_layout,
    list_approvals,
    list_tasks,
    result_exists,
    save_result,
    save_task,
    task_exists,
    utcnow_iso,
    write_json,
    remove_task,
)


@dataclass(frozen=True)
class SupervisorOptions:
    max_tasks: int = 25
    seed_from_discovery: bool = True
    seed_only: bool = False
    write_wiki: bool = True
    allowed_agents: tuple[str, ...] = ()


def _matches_rule(rule: RouteRule, result: TaskResult) -> bool:
    for key, value in rule.when_output_equals.items():
        if str(result.outputs.get(key, "")) != value:
            return False
    for key, candidates in rule.when_output_in.items():
        if str(result.outputs.get(key, "")) not in {str(item) for item in candidates}:
            return False
    return True


def _spawn_tasks_from_rule(rule: RouteRule, result: TaskResult, source_task: AgentTask) -> list[TaskSpawn]:
    if rule.mode == "per_source_blogger":
        source_bloggers = list(result.outputs.get("source_bloggers") or [])
        return [
            TaskSpawn(
                task_type=rule.downstream_task_type,
                entity_refs={
                    "brand_handle": str(result.outputs.get("brand_handle") or source_task.entity_refs.get("brand_handle") or ""),
                    "blogger_handle": str(blogger_handle),
                },
                inputs={
                    "brand_snapshot_path": str(result.outputs.get("brand_snapshot_path") or source_task.inputs.get("brand_snapshot_path") or ""),
                    "score_path": str(result.outputs.get("score_path") or source_task.inputs.get("score_path") or ""),
                    "dossier_path": str(result.outputs.get("dossier_path") or source_task.inputs.get("dossier_path") or ""),
                    "evidence_bundle_path": str(result.outputs.get("evidence_bundle_path") or source_task.inputs.get("evidence_bundle_path") or ""),
                    "evidence_report_path": str(result.outputs.get("evidence_report_path") or source_task.inputs.get("evidence_report_path") or ""),
                    "intelligence_packet_path": str(result.outputs.get("intelligence_packet_path") or source_task.inputs.get("intelligence_packet_path") or ""),
                    "arbiter_report_path": str(result.outputs.get("arbiter_report_path") or source_task.inputs.get("arbiter_report_path") or ""),
                    "media_report_path": str(result.outputs.get("media_report_path") or source_task.inputs.get("media_report_path") or ""),
                    "brand_handle": str(result.outputs.get("brand_handle") or source_task.entity_refs.get("brand_handle") or ""),
                    "blogger_handle": str(blogger_handle),
                    "supporting_stats": dict(result.outputs.get("supporting_stats") or source_task.inputs.get("supporting_stats") or {}),
                },
                source_task_id=source_task.task_id,
                source_run_id=source_task.source_run_id,
            )
            for blogger_handle in source_bloggers
        ]

    entity_refs = {
        "brand_handle": str(result.outputs.get("brand_handle") or source_task.entity_refs.get("brand_handle") or ""),
        "blogger_handle": str(result.outputs.get("blogger_handle") or source_task.entity_refs.get("blogger_handle") or ""),
    }
    if source_task.task_type == "media_intelligence.analyze_recent_media" and rule.downstream_task_type == "brand_arbiter.evaluate_case":
        entity_refs["analysis_stage"] = "media_enriched"
    elif source_task.entity_refs.get("analysis_stage"):
        entity_refs["analysis_stage"] = str(source_task.entity_refs.get("analysis_stage") or "")

    return [
        TaskSpawn(
            task_type=rule.downstream_task_type,
            entity_refs=entity_refs,
            inputs={
                "brand_snapshot_path": str(result.outputs.get("brand_snapshot_path") or source_task.inputs.get("brand_snapshot_path") or ""),
                "score_path": str(result.outputs.get("score_path") or source_task.inputs.get("score_path") or ""),
                "dossier_path": str(result.outputs.get("dossier_path") or source_task.inputs.get("dossier_path") or ""),
                "evidence_bundle_path": str(result.outputs.get("evidence_bundle_path") or source_task.inputs.get("evidence_bundle_path") or ""),
                "evidence_report_path": str(result.outputs.get("evidence_report_path") or source_task.inputs.get("evidence_report_path") or ""),
                "intelligence_packet_path": str(result.outputs.get("intelligence_packet_path") or source_task.inputs.get("intelligence_packet_path") or ""),
                "arbiter_report_path": str(result.outputs.get("arbiter_report_path") or source_task.inputs.get("arbiter_report_path") or ""),
                "media_report_path": str(result.outputs.get("media_report_path") or source_task.inputs.get("media_report_path") or ""),
                "decision_path": str(result.outputs.get("decision_path") or source_task.inputs.get("decision_path") or ""),
                "pitch_path": str(result.outputs.get("pitch_path") or source_task.inputs.get("pitch_path") or ""),
                "brand_handle": str(result.outputs.get("brand_handle") or source_task.entity_refs.get("brand_handle") or ""),
                "blogger_handle": str(result.outputs.get("blogger_handle") or source_task.entity_refs.get("blogger_handle") or ""),
                "reason": str(result.outputs.get("recommended_action") or ""),
                "supporting_stats": dict(result.outputs.get("supporting_stats") or source_task.inputs.get("supporting_stats") or {}),
            },
            source_task_id=source_task.task_id,
            source_run_id=source_task.source_run_id,
        )
    ]


def _materialize_spawn(project_root: Path, paths: ControlPlanePaths, spawn: TaskSpawn, task_contracts):
    contract = task_contracts[spawn.task_type]
    spawn_inputs = dict(spawn.inputs)
    if spawn.task_type == "conversation.send_message":
        spawn_inputs["allow_live_send"] = True
    task = AgentTask(
        task_id=build_stable_task_id(spawn.task_type, spawn.entity_refs),
        task_type=spawn.task_type,
        assigned_agent=contract.assigned_agent,
        status="pending",
        priority=spawn.priority,
        created_at_iso=utcnow_iso(),
        updated_at_iso=utcnow_iso(),
        source_run_id=spawn.source_run_id,
        source_task_id=spawn.source_task_id,
        entity_refs=dict(spawn.entity_refs),
        inputs=spawn_inputs,
        max_attempts=contract.max_attempts,
        requires_browser=contract.requires_browser,
        required_profile_capability=contract.required_profile_capability,
        requires_human_approval=contract.requires_human_approval,
        approval_scope=contract.approval_scope,
    )
    if task_exists(paths, task.task_id) or result_exists(paths, task.task_id):
        return None
    save_task(paths, task, "inbox")
    return task


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
        task = _materialize_spawn(project_root, paths, spawn, task_contracts)
        if task is not None:
            promoted += 1
    return promoted


def _write_run_summary(paths: ControlPlanePaths, summary: dict):
    path = paths.output_root / "run_summary.json"
    write_json(path, summary)
    return path


def run_supervisor(project_root: Path, options: SupervisorOptions | None = None) -> dict:
    options = options or SupervisorOptions()
    paths = ensure_control_plane_layout(project_root)
    task_contracts = load_task_type_contracts(project_root)
    routing_rules = load_routing_rules(project_root)
    profile_pool = load_profile_pool(project_root)

    seeded_count = 0
    if options.seed_from_discovery:
        seeded_count = len(seed_brand_intelligence_tasks(project_root, paths))

    promoted_count = _promote_approved_tasks(project_root, paths, task_contracts)

    processed_count = 0
    created_count = 0
    approval_count = 0
    failed_count = 0
    processed_task_ids: list[str] = []

    if not options.seed_only and options.max_tasks > 0:
        for task_path, task in list_tasks(paths, "inbox"):
            if options.allowed_agents and task.assigned_agent not in options.allowed_agents:
                continue
            if processed_count >= options.max_tasks:
                break

            lease_profile_key = ""
            try:
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
                save_task(paths, task, "completed")
                save_result(paths, result)
                processed_task_ids.append(task.task_id)
                processed_count += 1

                for rule in routing_rules.get(task.task_type, []):
                    if not _matches_rule(rule, result):
                        continue
                    for spawn in _spawn_tasks_from_rule(rule, result, task):
                        if not spawn.entity_refs.get("brand_handle"):
                            continue
                        if rule.requires_approval:
                            create_approval_record(
                                paths,
                                scope=rule.approval_scope,
                                requested_by_agent=task.assigned_agent,
                                source_task=task,
                                proposed_task=spawn,
                                payload_ref=str(
                                    result.outputs.get("draft_path")
                                    or result.outputs.get("pitch_path")
                                    or result.outputs.get("decision_path")
                                    or ""
                                ),
                                summary=result.summary,
                            )
                            approval_count += 1
                            continue
                        created_task = _materialize_spawn(project_root, paths, spawn, task_contracts)
                        if created_task is not None:
                            created_count += 1
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
        "created_downstream_tasks": created_count,
        "created_approvals": approval_count,
        "failed_tasks": failed_count,
        "processed_task_ids": processed_task_ids,
        "pending_approvals": len(list_approvals(paths, "pending")),
        "approvals_index": str(approvals_index),
    }
    _write_run_summary(paths, summary)
    return summary
