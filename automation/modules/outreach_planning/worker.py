from __future__ import annotations

from pathlib import Path
import json

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso

from .state import OutreachPlanningState


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"Required planning input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_outreach_planning_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    brand_handle = str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or "")
    blogger_handle = str(task.entity_refs.get("blogger_handle") or task.inputs.get("blogger_handle") or "")
    score_payload = _load_json(str(task.inputs.get("score_path", "")))
    snapshot = _load_json(str(task.inputs.get("brand_snapshot_path", "")))

    overall_score = int(score_payload.get("overall_score", 0) or 0)
    risk_score = int(score_payload.get("risk_score", 0) or 0)
    niche = str(snapshot.get("niche", "") or "")
    external_link = str(snapshot.get("external_link", "") or "")
    profile_url = str(snapshot.get("profile_url", "") or "")

    should_contact = overall_score >= 65 and risk_score < 60
    if "instagram.com" in profile_url:
        chosen_channel = "instagram_dm"
    elif "mailto:" in external_link or "@" in external_link:
        chosen_channel = "email"
    else:
        chosen_channel = "instagram_dm"

    if not should_contact:
        recommended_action = "hold" if overall_score >= 55 else "validate"
    else:
        recommended_action = "prepare_draft"

    angle = (
        f"Anchor outreach on {niche or 'brand-fit'} relevance for @{blogger_handle} and reference observed sponsored context."
        if blogger_handle
        else f"Anchor outreach on {niche or 'brand-fit'} relevance and discovery evidence."
    )
    rationale = (
        f"overall_score={overall_score}, risk_score={risk_score}, chosen_channel={chosen_channel}, "
        f"external_link={'present' if external_link else 'missing'}"
    )

    pair_key = f"{_slug(brand_handle)}__{_slug(blogger_handle or 'global')}"
    output_dir = project_root / "output" / "outreach_planning" / pair_key
    output_dir.mkdir(parents=True, exist_ok=True)
    decision_path = output_dir / "decision.json"
    pitch_path = output_dir / "pitch.md"

    decision_payload = {
        "brand_handle": brand_handle,
        "blogger_handle": blogger_handle,
        "should_contact": should_contact,
        "chosen_channel": chosen_channel,
        "recommended_action": recommended_action,
        "angle": angle,
        "rationale": rationale,
    }
    decision_path.write_text(json.dumps(decision_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pitch_path.write_text(
        "\n".join(
            [
                f"# Outreach Plan @{brand_handle} -> @{blogger_handle or 'unknown'}",
                "",
                f"- Recommended action: {recommended_action}",
                f"- Should contact: {'yes' if should_contact else 'no'}",
                f"- Channel: {chosen_channel}",
                "",
                "## Angle",
                angle,
                "",
                "## Rationale",
                rationale,
                "",
            ]
        ),
        encoding="utf-8-sig",
    )

    state_path = project_root / "automation" / "state" / "outreach_planning_state.json"
    state = OutreachPlanningState.load(state_path)
    state.current_pair_key = pair_key
    state.decisions[pair_key] = decision_payload
    state.drafts[pair_key] = {"pitch_path": str(pitch_path)}
    if pair_key not in state.completed_pair_keys:
        state.completed_pair_keys.append(pair_key)
    state.current_pair_key = ""
    state.save(state_path)

    evidence_refs = [str(decision_path), str(pitch_path), str(task.inputs.get("score_path", ""))]
    decision_refs: list[str] = []
    if write_wiki:
        campaign_page = project_root / "knowledge" / "llm_wiki" / "campaigns" / f"{pair_key}.md"
        decision_page = project_root / "knowledge" / "llm_wiki" / "decisions" / f"outreach_plan__{pair_key}.md"
        playbook_page = project_root / "knowledge" / "llm_wiki" / "playbooks" / f"{_slug(niche or 'generic')}_outreach.md"
        campaign_page.parent.mkdir(parents=True, exist_ok=True)
        decision_page.parent.mkdir(parents=True, exist_ok=True)
        playbook_page.parent.mkdir(parents=True, exist_ok=True)
        campaign_page.write_text(
            "\n".join(
                [
                    f"# Campaign @{brand_handle} x @{blogger_handle or 'unknown'}",
                    "",
                    f"- Status: {recommended_action}",
                    f"- Channel: {chosen_channel}",
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
        if not playbook_page.exists():
            playbook_page.write_text(
                "\n".join(
                    [
                        f"# Outreach Playbook {niche or 'generic'}",
                        "",
                        "- Start with the blogger-brand fit visible in discovery evidence.",
                        "- Keep the first touch short and concrete.",
                        "- Do not promise deliverables before approval.",
                        "",
                    ]
                ),
                encoding="utf-8-sig",
            )
        decision_refs.extend([str(campaign_page), str(decision_page), str(playbook_page)])

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Outreach plan prepared for @{brand_handle} and @{blogger_handle or 'unknown'}.",
        confidence="high" if should_contact and overall_score >= 75 else "medium",
        outputs={
            "brand_handle": brand_handle,
            "blogger_handle": blogger_handle,
            "should_contact": should_contact,
            "chosen_channel": chosen_channel,
            "recommended_action": recommended_action,
            "decision_path": str(decision_path),
            "pitch_path": str(pitch_path),
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path", "")),
        },
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
    )
