from __future__ import annotations

from pathlib import Path
import json

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso

from .state import FeedbackValidationState


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"Validation input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_validation_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    if task.task_type not in {"validation.review_brand_case", "validation.review_brand_risk", "validation.review_failed_task"}:
        raise RuntimeError(f"Unsupported validation task type: {task.task_type}")

    brand_handle = str(task.entity_refs.get("brand_handle") or task.inputs.get("brand_handle") or "")
    snapshot = _load_json(str(task.inputs.get("brand_snapshot_path", ""))) if task.inputs.get("brand_snapshot_path") else {}
    intelligence_packet = _load_json(str(task.inputs.get("intelligence_packet_path", ""))) if task.inputs.get("intelligence_packet_path") else {}
    legacy_score = _load_json(str(task.inputs.get("score_path", ""))) if task.inputs.get("score_path") else {}
    media_report = _load_json(str(task.inputs.get("media_report_path", ""))) if task.inputs.get("media_report_path") else {}
    reason = str(task.inputs.get("reason") or task.task_type)

    risk_score = int(intelligence_packet.get("risk_score", legacy_score.get("risk_score", 0)) or 0)
    evidence_strength = str(intelligence_packet.get("evidence_strength", "") or "")
    confidence = str(intelligence_packet.get("confidence", "") or "")
    findings: list[str] = []

    if str(snapshot.get("account_kind", "") or "") == "service_provider":
        findings.append("Discovery classified the profile as service_provider, so brand identity is ambiguous.")
    if not snapshot.get("external_link"):
        findings.append("External link is missing, which weakens business-account confidence.")
    if confidence == "low":
        findings.append("Brand arbiter confidence is low, so the case should not move to outreach without deeper review.")
    if evidence_strength == "weak":
        findings.append("Evidence density is weak; the current packet is not strong enough for confident outreach.")
    if legacy_score and int(legacy_score.get("overall_score", 0) or 0) < 60:
        findings.append("Legacy intelligence score remains below the contact threshold.")
    if risk_score >= 60:
        findings.append("Risk score is high enough to require manual validation before any outreach.")
    if intelligence_packet.get("research_gaps"):
        findings.extend(str(item) for item in intelligence_packet.get("research_gaps") or [] if str(item).strip())
    if media_report:
        findings.append("Media enrichment was attached and should be treated as personalization support, not as primary proof.")
    if not findings:
        findings.append("No blocking contradictions found; task was opened for manual review context only.")

    output_dir = project_root / "output" / "feedback_validation" / _slug(brand_handle or "unknown")
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "review.md"
    finding_path = output_dir / "finding.json"

    review_path.write_text(
        "\n".join(
            [
                f"# Validation @{brand_handle or 'unknown'}",
                "",
                f"- Task type: {task.task_type}",
                f"- Reason: {reason}",
                "",
                "## Findings",
                *[f"- {item}" for item in findings],
                "",
            ]
        ),
        encoding="utf-8-sig",
    )
    finding_payload = {
        "brand_handle": brand_handle,
        "task_type": task.task_type,
        "reason": reason,
        "findings": findings,
        "recommended_action": "manual_review",
    }
    finding_path.write_text(json.dumps(finding_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    state_path = project_root / "automation" / "state" / "feedback_validation_state.json"
    state = FeedbackValidationState.load(state_path)
    state.current_brand_handle = brand_handle
    state.tasks[task.task_id] = {"reason": reason, "task_type": task.task_type}
    state.findings[brand_handle or task.task_id] = finding_payload
    if brand_handle and brand_handle not in state.completed_brand_handles:
        state.completed_brand_handles.append(brand_handle)
    state.current_brand_handle = ""
    state.save(state_path)

    decision_refs: list[str] = []
    if write_wiki:
        decision_page = project_root / "knowledge" / "llm_wiki" / "decisions" / f"validation__{_slug(brand_handle or task.task_id)}.md"
        evidence_page = project_root / "knowledge" / "llm_wiki" / "evidence" / f"validation__{_slug(brand_handle or task.task_id)}.md"
        decision_page.parent.mkdir(parents=True, exist_ok=True)
        evidence_page.parent.mkdir(parents=True, exist_ok=True)
        decision_page.write_text(
            "\n".join(
                [
                    f"# Validation Decision @{brand_handle or 'unknown'}",
                    "",
                    f"- Task type: {task.task_type}",
                    f"- Recommended action: manual_review",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        evidence_page.write_text(
            "\n".join(
                [
                    f"# Validation Evidence @{brand_handle or 'unknown'}",
                    "",
                    *[f"- {item}" for item in findings],
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.extend([str(decision_page), str(evidence_page)])

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Validation findings recorded for @{brand_handle or 'unknown'}.",
        confidence="medium",
        outputs={
            "brand_handle": brand_handle,
            "recommended_action": "manual_review",
            "review_path": str(review_path),
            "finding_path": str(finding_path),
        },
        evidence_refs=[str(review_path), str(finding_path)],
        decision_refs=decision_refs,
    )
