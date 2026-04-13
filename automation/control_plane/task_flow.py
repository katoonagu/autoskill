from __future__ import annotations

from pathlib import Path

from .approvals import create_approval_record
from .models import AgentTask, RouteRule, TaskResult, TaskSpawn
from .storage import (
    ControlPlanePaths,
    build_stable_task_id,
    remove_task,
    result_exists,
    save_result,
    save_task,
    task_exists,
    utcnow_iso,
)


def matches_rule(rule: RouteRule, result: TaskResult) -> bool:
    for key, value in rule.when_output_equals.items():
        if str(result.outputs.get(key, "")) != value:
            return False
    for key, candidates in rule.when_output_in.items():
        if str(result.outputs.get(key, "")) not in {str(item) for item in candidates}:
            return False
    return True


def spawn_tasks_from_rule(rule: RouteRule, result: TaskResult, source_task: AgentTask) -> list[TaskSpawn]:
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


def materialize_spawn(project_root: Path, paths: ControlPlanePaths, spawn: TaskSpawn, task_contracts):
    contract = task_contracts[spawn.task_type]
    spawn_inputs = dict(spawn.inputs)
    if spawn.task_type == "conversation.send_message":
        spawn_inputs["allow_live_send"] = True
    created_at_iso = utcnow_iso()
    task = AgentTask(
        task_id=build_stable_task_id(spawn.task_type, spawn.entity_refs),
        task_type=spawn.task_type,
        assigned_agent=contract.assigned_agent,
        status="pending",
        priority=spawn.priority,
        created_at_iso=created_at_iso,
        updated_at_iso=created_at_iso,
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


def finalize_success(
    project_root: Path,
    paths: ControlPlanePaths,
    task: AgentTask,
    result: TaskResult,
    routing_rules,
    task_contracts,
) -> tuple[int, int]:
    remove_task(paths, task.task_id)
    task.status = "completed"
    task.updated_at_iso = result.completed_at_iso
    task.outputs = dict(result.outputs)
    task.evidence_refs = list(result.evidence_refs)
    save_task(paths, task, "completed")
    save_result(paths, result)

    created_count = 0
    approval_count = 0
    for rule in routing_rules.get(task.task_type, []):
        if not matches_rule(rule, result):
            continue
        for spawn in spawn_tasks_from_rule(rule, result, task):
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
            created_task = materialize_spawn(project_root, paths, spawn, task_contracts)
            if created_task is not None:
                created_count += 1
    return created_count, approval_count
