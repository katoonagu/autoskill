from __future__ import annotations

from pathlib import Path
import json

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso

from .state import BrandIntelligenceState
from .web_research import run_brand_web_research, write_research_report


def _score_from_level(level: str, *, low: int, medium: int, high: int) -> int:
    normalized = str(level or "").strip().lower()
    if normalized == "high":
        return high
    if normalized == "medium":
        return medium
    return low


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_brand_snapshot(task: AgentTask) -> dict:
    path = Path(str(task.inputs.get("brand_snapshot_path", "")))
    if not path.exists():
        raise RuntimeError(f"Brand snapshot not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_brand_intelligence_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    snapshot = _load_brand_snapshot(task)
    handle = str(snapshot.get("handle") or task.entity_refs.get("brand_handle") or "")
    state_path = project_root / "automation" / "state" / "brand_intelligence_state.json"
    state = BrandIntelligenceState.load(state_path)
    state.current_brand_handle = handle

    outreach_fit = str(snapshot.get("outreach_fit", "") or "")
    brand_likelihood = str(snapshot.get("brand_likelihood", "") or "")
    ad_likelihood = str(snapshot.get("ad_likelihood", "") or "")
    account_kind = str(snapshot.get("account_kind", "") or "")
    source_bloggers = list(task.inputs.get("source_bloggers") or [])
    sources_count = len(snapshot.get("sources", []) or [])
    research_report = run_brand_web_research(snapshot)

    fit_score = _score_from_level(outreach_fit, low=35, medium=62, high=84)
    commercial_signal = _score_from_level(brand_likelihood, low=30, medium=60, high=85)
    ad_signal = _score_from_level(ad_likelihood, low=35, medium=58, high=78)
    research_boost = 0
    if research_report.official_site_found:
        research_boost += 8
    if research_report.positive_signal_count:
        research_boost += min(8, research_report.positive_signal_count * 2)
    if research_report.tone == "negative":
        research_boost -= 10
    reputation_score = min(92, max(25, int((commercial_signal + ad_signal + fit_score) / 3) + research_boost))

    risk_score = 22
    risk_notes: list[str] = []
    if account_kind == "service_provider":
        risk_score += 18
        risk_notes.append("service-provider profile can be a person-brand false positive")
    if brand_likelihood == "low":
        risk_score += 18
        risk_notes.append("brand-likelihood is low in discovery output")
    if not snapshot.get("external_link"):
        risk_score += 8
        risk_notes.append("no external link present")
    if sources_count <= 1:
        risk_score += 10
        risk_notes.append("single-source brand mention only")
    if research_report.negative_signal_count:
        risk_score += min(18, research_report.negative_signal_count * 4)
        risk_notes.append(f"web research surfaced {research_report.negative_signal_count} negative lexical signals")
    if research_report.tone == "negative":
        risk_score += 8
        risk_notes.append("overall web-research tone is negative")
    risk_score = min(risk_score, 95)

    overall_score = max(0, min(100, int((reputation_score * 0.35) + (fit_score * 0.4) + ((100 - risk_score) * 0.25))))
    recommended_action = "plan_outreach"
    if overall_score < 58 or risk_score >= 60:
        recommended_action = "validate"
    elif overall_score < 68:
        recommended_action = "hold"

    dossier_dir = project_root / "output" / "brand_intelligence" / _slug(handle)
    dossier_dir.mkdir(parents=True, exist_ok=True)
    dossier_path = dossier_dir / "dossier.md"
    score_path = dossier_dir / "score.json"
    research_path = dossier_dir / "web_research.json"
    write_research_report(research_path, research_report)

    summary_lines = [
        f"# Brand Intelligence @{handle}",
        "",
        f"- Overall score: {overall_score}",
        f"- Reputation score: {reputation_score}",
        f"- Fit score: {fit_score}",
        f"- Risk score: {risk_score}",
        f"- Recommended action: {recommended_action}",
        f"- Account kind: {account_kind or 'unknown'}",
        f"- Niche: {snapshot.get('niche', '') or 'unknown'}",
        f"- Category label: {snapshot.get('category_label', '') or 'unknown'}",
        f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
        f"- Web research tone: {research_report.tone}",
        f"- Geo: {research_report.geo}",
        f"- Price segment: {research_report.price_segment}",
        f"- Review source count: {research_report.review_source_count}",
        f"- Official site found: {'yes' if research_report.official_site_found else 'no'}",
        "",
        "## Signals",
        f"- Brand likelihood: {brand_likelihood or 'unknown'}",
        f"- Outreach fit: {outreach_fit or 'unknown'}",
        f"- Ad likelihood: {ad_likelihood or 'unknown'}",
        "",
        "## Web Research Notes",
    ]
    for note in research_report.summary_notes:
        summary_lines.append(f"- {note}")
    summary_lines.extend(
        [
            "",
            "## Search Results",
        ]
    )
    for item in research_report.search_results:
        summary_lines.append(f"- {item.title} | {item.url} | {item.snippet}")
    summary_lines.extend(
        [
            "",
            "## Notes",
        ]
    )
    for note in risk_notes or ["No major risk notes triggered by the discovery snapshot."]:
        summary_lines.append(f"- {note}")
    summary_lines.extend(
        [
            "",
            "## Bio",
            str(snapshot.get("bio", "") or "none"),
            "",
            "## Reasoning",
            str(snapshot.get("reasoning", "") or "none"),
            "",
        ]
    )
    dossier_path.write_text("\n".join(summary_lines), encoding="utf-8-sig")
    score_payload = {
        "brand_handle": handle,
        "overall_score": overall_score,
        "reputation_score": reputation_score,
        "fit_score": fit_score,
        "risk_score": risk_score,
        "recommended_action": recommended_action,
        "source_bloggers": source_bloggers,
        "tone": research_report.tone,
        "geo": research_report.geo,
        "price_segment": research_report.price_segment,
        "review_source_count": research_report.review_source_count,
        "official_site_found": research_report.official_site_found,
        "web_research_path": str(research_path),
    }
    score_path.write_text(json.dumps(score_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    state.dossiers[handle] = {"dossier_path": str(dossier_path)}
    state.scores[handle] = score_payload
    if handle not in state.completed_brand_handles:
        state.completed_brand_handles.append(handle)
    state.current_brand_handle = ""
    state.save(state_path)

    evidence_refs = [str(dossier_path), str(score_path), str(research_path), str(task.inputs.get("brand_snapshot_path", ""))]
    decision_refs: list[str] = []
    if write_wiki:
        brand_page = project_root / "knowledge" / "llm_wiki" / "brands" / f"{_slug(handle)}.md"
        decision_page = project_root / "knowledge" / "llm_wiki" / "decisions" / f"brand_intelligence__{_slug(handle)}.md"
        brand_page.parent.mkdir(parents=True, exist_ok=True)
        decision_page.parent.mkdir(parents=True, exist_ok=True)
        brand_page.write_text(
            "\n".join(
                [
                    f"# Brand @{handle}",
                    "",
                    f"- Overall score: {overall_score}",
                    f"- Recommended action: {recommended_action}",
                    f"- Risk score: {risk_score}",
                    f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
                    f"- Dossier: {dossier_path.as_posix()}",
                    f"- Web research: {research_path.as_posix()}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_page.write_text(
            "\n".join(
                [
                    f"# Decision Brand Intelligence @{handle}",
                    "",
                    f"- Confidence: {'high' if overall_score >= 75 else 'medium' if overall_score >= 55 else 'low'}",
                    f"- Recommended action: {recommended_action}",
                    f"- Evidence: {', '.join(path for path in evidence_refs if path)}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.extend([str(brand_page), str(decision_page)])

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Brand @{handle} scored for downstream routing.",
        confidence="high" if overall_score >= 75 else "medium" if overall_score >= 55 else "low",
        outputs={
            "brand_handle": handle,
            "overall_score": overall_score,
            "risk_score": risk_score,
            "fit_score": fit_score,
            "reputation_score": reputation_score,
            "recommended_action": recommended_action,
            "source_bloggers": source_bloggers,
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path", "")),
            "dossier_path": str(dossier_path),
            "score_path": str(score_path),
            "web_research_path": str(research_path),
        },
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
    )
