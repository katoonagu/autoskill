from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re

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


def _parse_datetime(raw_value: str) -> datetime | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_source_bloggers(task: AgentTask, snapshot: dict) -> list[str]:
    bloggers = [str(item).strip() for item in (task.inputs.get("source_bloggers") or []) if str(item).strip()]
    if bloggers:
        return sorted(dict.fromkeys(bloggers))
    extracted = [
        str(source.get("blogger_handle") or "").strip()
        for source in (snapshot.get("sources") or [])
        if str(source.get("blogger_handle") or "").strip()
    ]
    return sorted(dict.fromkeys(extracted))


def _extract_follower_count(text: str) -> int:
    match = re.search(r"([\d,\.]+)\s+Followers", str(text or ""), re.IGNORECASE)
    if not match:
        return 0
    numeric = re.sub(r"[^\d]", "", match.group(1))
    return int(numeric or 0)


def _derive_supporting_stats(snapshot: dict, research_report, source_bloggers: list[str]) -> dict:
    now = datetime.now(timezone.utc)
    sources = list(snapshot.get("sources") or [])
    source_dates = [_parse_datetime(source.get("post_date_iso") or "") for source in sources]
    source_dates = [item for item in source_dates if item is not None]
    recent_30d = sum(1 for item in source_dates if item >= now - timedelta(days=30))
    recent_90d = sum(1 for item in source_dates if item >= now - timedelta(days=90))
    ad_high = sum(1 for source in sources if str(source.get("ad_likelihood") or "").strip().lower() == "high")
    ad_medium = sum(1 for source in sources if str(source.get("ad_likelihood") or "").strip().lower() == "medium")
    follower_count = _extract_follower_count(str(snapshot.get("followers_text") or snapshot.get("bio") or ""))
    official_signal = 1 if research_report.official_site_found else 0
    positive_signal_count = int(research_report.positive_signal_count or 0)
    negative_signal_count = int(research_report.negative_signal_count or 0)

    if official_signal and (positive_signal_count >= 2 or len(source_bloggers) >= 2):
        brand_value_tier = "high"
    elif official_signal or positive_signal_count >= 1 or follower_count >= 5000:
        brand_value_tier = "medium"
    else:
        brand_value_tier = "low"

    personalization_gap = len(snapshot.get("source_posts") or []) < 2 or not str(snapshot.get("reasoning") or "").strip()
    signal_conflict = (
        str(snapshot.get("account_kind") or "").strip().lower() == "service_provider"
        or (str(snapshot.get("brand_likelihood") or "").strip().lower() == "high" and negative_signal_count >= 2)
        or (research_report.tone == "negative" and positive_signal_count >= 2)
    )

    return {
        "unique_blogger_count": len(source_bloggers),
        "source_posts_count": len(snapshot.get("source_posts") or []),
        "recent_mentions_30d": recent_30d,
        "recent_mentions_90d": recent_90d,
        "high_ad_likelihood_mentions": ad_high,
        "medium_ad_likelihood_mentions": ad_medium,
        "follower_count": follower_count,
        "official_site_found": research_report.official_site_found,
        "review_source_count": research_report.review_source_count,
        "positive_signal_count": positive_signal_count,
        "negative_signal_count": negative_signal_count,
        "brand_value_tier": brand_value_tier,
        "personalization_gap": personalization_gap,
        "signal_conflict": signal_conflict,
    }


def run_brand_intelligence_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    if task.task_type != "brand_intelligence.collect_evidence":
        raise RuntimeError(f"Unsupported brand intelligence task type: {task.task_type}")

    snapshot = _load_brand_snapshot(task)
    handle = str(snapshot.get("handle") or task.entity_refs.get("brand_handle") or "")
    state_path = project_root / "automation" / "state" / "brand_intelligence_state.json"
    state = BrandIntelligenceState.load(state_path)
    state.current_brand_handle = handle

    source_bloggers = _load_source_bloggers(task, snapshot)
    research_report = run_brand_web_research(snapshot)
    supporting_stats = _derive_supporting_stats(snapshot, research_report, source_bloggers)
    evidence_dir = project_root / "output" / "brand_intelligence" / _slug(handle)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    web_research_path = evidence_dir / "web_research.json"
    evidence_bundle_path = evidence_dir / "evidence_bundle.json"
    evidence_report_path = evidence_dir / "evidence_report.md"
    write_research_report(web_research_path, research_report)

    source_refs = []
    for source in snapshot.get("sources") or []:
        source_refs.append(
            {
                "blogger_handle": str(source.get("blogger_handle") or "").strip(),
                "post_url": str(source.get("post_url") or "").strip(),
                "post_date_iso": str(source.get("post_date_iso") or "").strip(),
                "ad_likelihood": str(source.get("ad_likelihood") or "").strip(),
                "caption_excerpt": str(source.get("caption_excerpt") or "").strip(),
            }
        )

    evidence_bundle = {
        "brand_handle": handle,
        "brand_name": str(snapshot.get("display_name") or handle),
        "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
        "discovery_snapshot": snapshot,
        "source_bloggers": source_bloggers,
        "source_blogger_refs": source_refs,
        "search_queries": list(research_report.search_queries),
        "search_results": [item.__dict__ for item in research_report.search_results],
        "page_summaries": [item.__dict__ for item in research_report.page_summaries],
        "review_signals": {
            "review_source_count": research_report.review_source_count,
            "tone": research_report.tone,
            "positive_signal_count": research_report.positive_signal_count,
            "negative_signal_count": research_report.negative_signal_count,
            "summary_notes": list(research_report.summary_notes),
        },
        "mention_statistics": supporting_stats,
        "media_summary_refs": [str(task.inputs.get("media_report_path") or "")] if task.inputs.get("media_report_path") else [],
        "derived_numeric_features": {
            "fit_signal_score": _score_from_level(str(snapshot.get("outreach_fit") or ""), low=35, medium=62, high=84),
            "brand_signal_score": _score_from_level(str(snapshot.get("brand_likelihood") or ""), low=30, medium=60, high=86),
            "ad_signal_score": _score_from_level(str(snapshot.get("ad_likelihood") or ""), low=35, medium=58, high=78),
        },
        "media_candidate_urls": list(snapshot.get("source_posts") or []),
    }
    evidence_bundle_path.write_text(json.dumps(evidence_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        f"# Evidence Bundle @{handle}",
        "",
        f"- Brand name: {snapshot.get('display_name') or handle}",
        f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
        f"- Official site found: {'yes' if research_report.official_site_found else 'no'}",
        f"- Review source count: {research_report.review_source_count}",
        f"- Web tone: {research_report.tone}",
        f"- Geo hint: {research_report.geo}",
        f"- Price segment: {research_report.price_segment}",
        "",
        "## Supporting Stats",
    ]
    for key, value in supporting_stats.items():
        report_lines.append(f"- {key}: {value}")
    report_lines.extend(
        [
            "",
            "## Web Research Notes",
        ]
    )
    for note in research_report.summary_notes:
        report_lines.append(f"- {note}")
    report_lines.extend(
        [
            "",
            "## Search Results",
        ]
    )
    for item in research_report.search_results:
        report_lines.append(f"- {item.title} | {item.url} | {item.snippet}")
    evidence_report_path.write_text("\n".join(report_lines), encoding="utf-8-sig")

    state.evidence_bundles[handle] = {
        "evidence_bundle_path": str(evidence_bundle_path),
        "supporting_stats": supporting_stats,
    }
    state.research_reports[handle] = {
        "web_research_path": str(web_research_path),
        "evidence_report_path": str(evidence_report_path),
    }
    if handle not in state.completed_brand_handles:
        state.completed_brand_handles.append(handle)
    state.current_brand_handle = ""
    state.save(state_path)

    evidence_refs = [
        str(evidence_bundle_path),
        str(evidence_report_path),
        str(web_research_path),
        str(task.inputs.get("brand_snapshot_path") or ""),
    ]
    decision_refs: list[str] = []
    if write_wiki:
        brand_page = project_root / "knowledge" / "llm_wiki" / "brands" / f"{_slug(handle)}.md"
        brand_page.parent.mkdir(parents=True, exist_ok=True)
        brand_page.write_text(
            "\n".join(
                [
                    f"# Brand @{handle}",
                    "",
                    f"- Evidence bundle: {evidence_bundle_path.as_posix()}",
                    f"- Evidence report: {evidence_report_path.as_posix()}",
                    f"- Web research: {web_research_path.as_posix()}",
                    f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.append(str(brand_page))

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Evidence collected for @{handle}.",
        confidence="high" if supporting_stats["official_site_found"] or supporting_stats["unique_blogger_count"] >= 2 else "medium",
        outputs={
            "brand_handle": handle,
            "brand_name": str(snapshot.get("display_name") or handle),
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
            "source_bloggers": source_bloggers,
            "web_research_path": str(web_research_path),
            "evidence_bundle_path": str(evidence_bundle_path),
            "evidence_report_path": str(evidence_report_path),
            "supporting_stats": supporting_stats,
        },
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
    )
