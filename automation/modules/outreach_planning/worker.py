from __future__ import annotations

from pathlib import Path
import json

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso

from .state import OutreachPlanningState


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str, *, label: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"{label} not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_outreach_planning_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    brand_handle = str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or "")
    blogger_handle = str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or "")
    intelligence_packet = _load_json(str(task.inputs.get("intelligence_packet_path") or ""), label="Intelligence packet")
    snapshot = _load_json(str(task.inputs.get("brand_snapshot_path") or ""), label="Brand snapshot")
    arbiter_report_path = str(task.inputs.get("arbiter_report_path") or intelligence_packet.get("arbiter_reasoning_ref") or "")

    verdict = str(intelligence_packet.get("verdict") or "hold")
    recommended_channel = str(intelligence_packet.get("recommended_channel") or "instagram_dm")
    recommended_angle = str(intelligence_packet.get("recommended_angle") or "")
    what_not_to_say = [str(item).strip() for item in (intelligence_packet.get("what_not_to_say") or []) if str(item).strip()]
    why_this_brand = str(intelligence_packet.get("why_this_brand") or "")
    why_now = str(intelligence_packet.get("why_now") or "")
    supporting_stats = dict(task.inputs.get("supporting_stats") or intelligence_packet.get("supporting_stats") or {})
    guardrail_lines = [f"- {item}" for item in what_not_to_say] or ["- No explicit guardrails provided."]
    stats_lines = [f"- {key}: {value}" for key, value in supporting_stats.items()] or ["- No supporting stats provided."]

    should_contact = verdict == "plan_outreach"
    if not should_contact:
        recommended_action = "validate" if str(intelligence_packet.get("recommended_action") or "") == "validate" else "hold"
    else:
        recommended_action = "prepare_draft"

    pair_key = f"{_slug(brand_handle)}__{_slug(blogger_handle or 'global')}"
    output_dir = project_root / "output" / "outreach_planning" / pair_key
    output_dir.mkdir(parents=True, exist_ok=True)
    decision_path = output_dir / "decision.json"
    pitch_path = output_dir / "pitch.md"

    rationale = (
        f"verdict={verdict}, channel={recommended_channel}, "
        f"outreach_readiness={int(intelligence_packet.get('outreach_readiness_score', 0) or 0)}, "
        f"risk={int(intelligence_packet.get('risk_score', 0) or 0)}"
    )
    decision_payload = {
        "brand_handle": brand_handle,
        "blogger_handle": blogger_handle,
        "should_contact": should_contact,
        "chosen_channel": recommended_channel,
        "recommended_action": recommended_action,
        "recommended_angle": recommended_angle,
        "why_this_brand": why_this_brand,
        "why_now": why_now,
        "what_not_to_say": what_not_to_say,
        "supporting_stats": supporting_stats,
        "arbiter_report_path": arbiter_report_path,
        "intelligence_packet_path": str(task.inputs.get("intelligence_packet_path") or ""),
        "rationale": rationale,
    }
    decision_path.write_text(json.dumps(decision_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    pitch_lines = [
        f"# Outreach Plan @{brand_handle} -> @{blogger_handle or 'unknown'}",
        "",
        f"- Recommended action: {recommended_action}",
        f"- Should contact: {'yes' if should_contact else 'no'}",
        f"- Channel: {recommended_channel}",
        f"- Arbiter report: {arbiter_report_path or 'none'}",
        "",
        "## Why This Brand",
        why_this_brand or "Insufficient arbiter context.",
        "",
        "## Why Now",
        why_now or "No timing hook provided.",
        "",
        "## Recommended Angle",
        recommended_angle or "Angle withheld because the case is not outreach-ready.",
        "",
        "## What Not To Say",
        *guardrail_lines,
        "",
    ]
    if should_contact:
        pitch_lines.extend(
            [
                "## Supporting Stats",
                *stats_lines,
                "",
            ]
        )
    else:
        pitch_lines.extend(
            [
                "## Status",
                "Pitch generation is blocked because the arbiter did not mark this case as outreach-ready.",
                "",
            ]
        )
    pitch_path.write_text("\n".join(pitch_lines), encoding="utf-8-sig")

    state_path = project_root / "automation" / "state" / "outreach_planning_state.json"
    state = OutreachPlanningState.load(state_path)
    state.current_pair_key = pair_key
    state.decisions[pair_key] = decision_payload
    state.drafts[pair_key] = {"pitch_path": str(pitch_path)}
    if pair_key not in state.completed_pair_keys:
        state.completed_pair_keys.append(pair_key)
    state.current_pair_key = ""
    state.save(state_path)

    evidence_refs = [str(decision_path), str(pitch_path), str(task.inputs.get("intelligence_packet_path") or "")]
    decision_refs: list[str] = []
    if write_wiki:
        campaign_page = project_root / "knowledge" / "llm_wiki" / "campaigns" / f"{pair_key}.md"
        decision_page = project_root / "knowledge" / "llm_wiki" / "decisions" / f"outreach_plan__{pair_key}.md"
        campaign_page.parent.mkdir(parents=True, exist_ok=True)
        decision_page.parent.mkdir(parents=True, exist_ok=True)
        campaign_page.write_text(
            "\n".join(
                [
                    f"# Campaign @{brand_handle} x @{blogger_handle or 'unknown'}",
                    "",
                    f"- Status: {recommended_action}",
                    f"- Channel: {recommended_channel}",
                    f"- Pitch path: {pitch_path.as_posix()}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_page.write_text(
            "\n".join(
                [
                    f"# Decision Outreach @{brand_handle} x @{blogger_handle or 'unknown'}",
                    "",
                    f"- Should contact: {'yes' if should_contact else 'no'}",
                    f"- Recommended action: {recommended_action}",
                    f"- Rationale: {rationale}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.extend([str(campaign_page), str(decision_page)])

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Outreach plan prepared for @{brand_handle} and @{blogger_handle or 'unknown'}.",
        confidence="high" if should_contact else "medium",
        outputs={
            "brand_handle": brand_handle,
            "blogger_handle": blogger_handle,
            "should_contact": should_contact,
            "chosen_channel": recommended_channel,
            "recommended_action": recommended_action,
            "decision_path": str(decision_path),
            "pitch_path": str(pitch_path),
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
            "intelligence_packet_path": str(task.inputs.get("intelligence_packet_path") or ""),
            "recommended_angle": recommended_angle,
            "why_this_brand": why_this_brand,
            "why_now": why_now,
            "what_not_to_say": what_not_to_say,
            "supporting_stats": supporting_stats,
        },
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
    )
