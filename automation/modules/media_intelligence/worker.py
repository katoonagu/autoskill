from __future__ import annotations

from pathlib import Path
import json
import re

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso
from automation.llm.clients import AutoskillLLMClient, LLMUnavailableError
from automation.llm.prompts.media_intelligence import build_media_analysis_prompt
from automation.llm.schemas import MEDIA_REPORT_SCHEMA

from .state import MediaIntelligenceState


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str, *, label: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"{label} not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_topics(texts: list[str]) -> list[str]:
    keywords = []
    combined = " ".join(texts).lower()
    for candidate in ("fashion", "beauty", "jewelry", "hotel", "travel", "lifestyle", "skin", "dress", "atelier", "premium"):
        if candidate in combined:
            keywords.append(candidate)
    return keywords or ["creator_context", "brand_visibility"]


def _heuristic_media_report(media_payload: dict) -> dict:
    sources = media_payload.get("sources") or []
    captions = [str(source.get("caption_excerpt") or "").strip() for source in sources if str(source.get("caption_excerpt") or "").strip()]
    urls = [str(item).strip() for item in (media_payload.get("media_candidate_urls") or []) if str(item).strip()]
    combined = " ".join(captions)
    creator_style = "editorial / integration-friendly" if any("@" in text for text in captions) else "generic creator style"
    integration_fit = "high" if len(captions) >= 2 else "medium" if captions else "low"
    comment_themes = ["Нет реальных comments в discovery snapshot; использовать как слабый сигнал."] if not media_payload.get("comments") else media_payload["comments"]

    return {
        "content_topics": _extract_topics(captions + urls),
        "brand_mentions": _extract_topics([combined]) if combined else [media_payload.get("brand_handle") or "brand_mention"],
        "audience_tone": "unknown",
        "comment_themes": comment_themes,
        "comment_sentiment": "unknown",
        "recurring_requests": ["Недостаточно comment-data для уверенных recurring requests."],
        "risk_flags": ["Comments absent or weak; do not use as primary evidence."],
        "creator_style": creator_style,
        "integration_fit": integration_fit,
        "use_as_signal": [
            "Использовать captions и source post URLs как контекст интеграции.",
            "Использовать media только для personalization, не для доказательства качества бренда.",
        ],
        "do_not_use_as_signal": [
            "Не считать отсутствие comments негативным brand signal.",
            "Не считать captions самостоятельным доказательством коммерческой силы бренда.",
        ],
    }


def _build_media_report(project_root: Path, media_payload: dict) -> dict:
    client = AutoskillLLMClient.from_project_root(project_root)
    if client.is_available():
        try:
            payload = client.analyze_media(media_payload, MEDIA_REPORT_SCHEMA, model=client.config.media_model)
            payload["llm_provider"] = client.config.provider
            return payload
        except (LLMUnavailableError, RuntimeError, ValueError):
            pass
    payload = _heuristic_media_report(media_payload)
    payload["llm_provider"] = "heuristic_fallback"
    return payload


def run_media_intelligence_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    if task.task_type != "media_intelligence.analyze_recent_media":
        raise RuntimeError(f"Unsupported media intelligence task type: {task.task_type}")

    evidence_bundle = _load_json(str(task.inputs.get("evidence_bundle_path") or ""), label="Evidence bundle")
    snapshot = dict(evidence_bundle.get("discovery_snapshot") or {})
    brand_handle = str(evidence_bundle.get("brand_handle") or task.entity_refs.get("brand_handle") or "")
    state_path = project_root / "automation" / "state" / "media_intelligence_state.json"
    state = MediaIntelligenceState.load(state_path)
    state.current_brand_handle = brand_handle

    media_payload = {
        "brand_handle": brand_handle,
        "brand_name": str(evidence_bundle.get("brand_name") or brand_handle),
        "media_candidate_urls": list(evidence_bundle.get("media_candidate_urls") or []),
        "sources": list(evidence_bundle.get("source_blogger_refs") or []),
        "comments": [],
        "supporting_stats": dict(evidence_bundle.get("mention_statistics") or {}),
        "profile_bio": str(snapshot.get("bio") or ""),
    }
    media_report = _build_media_report(project_root, media_payload)

    output_dir = project_root / "output" / "media_intelligence" / _slug(brand_handle)
    output_dir.mkdir(parents=True, exist_ok=True)
    media_report_path = output_dir / "media_report.json"
    media_markdown_path = output_dir / "media_report.md"
    media_report_path.write_text(json.dumps(media_report, ensure_ascii=False, indent=2), encoding="utf-8")
    media_markdown_path.write_text(
        "\n".join(
            [
                f"# Media Intelligence @{brand_handle}",
                "",
                f"- Provider: {media_report['llm_provider']}",
                f"- Audience tone: {media_report['audience_tone']}",
                f"- Comment sentiment: {media_report['comment_sentiment']}",
                f"- Creator style: {media_report['creator_style']}",
                f"- Integration fit: {media_report['integration_fit']}",
                "",
                "## Use As Signal",
                *[f"- {item}" for item in media_report.get("use_as_signal") or []],
                "",
                "## Do Not Use As Signal",
                *[f"- {item}" for item in media_report.get("do_not_use_as_signal") or []],
                "",
            ]
        ),
        encoding="utf-8-sig",
    )

    state.reports[brand_handle] = {
        "media_report_path": str(media_report_path),
        "media_markdown_path": str(media_markdown_path),
    }
    if brand_handle not in state.completed_brand_handles:
        state.completed_brand_handles.append(brand_handle)
    state.current_brand_handle = ""
    state.save(state_path)

    decision_refs: list[str] = []
    if write_wiki:
        evidence_page = project_root / "knowledge" / "llm_wiki" / "evidence" / f"media__{_slug(brand_handle)}.md"
        evidence_page.parent.mkdir(parents=True, exist_ok=True)
        evidence_page.write_text(
            "\n".join(
                [
                    f"# Media Evidence @{brand_handle}",
                    "",
                    f"- Media report: {media_report_path.as_posix()}",
                    f"- Markdown report: {media_markdown_path.as_posix()}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.append(str(evidence_page))

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Media enrichment prepared for @{brand_handle}.",
        confidence="medium",
        outputs={
            "brand_handle": brand_handle,
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
            "media_report_path": str(media_report_path),
            "media_markdown_path": str(media_markdown_path),
            "recommended_action": "media_ready",
        },
        evidence_refs=[str(media_report_path), str(media_markdown_path), str(task.inputs.get("evidence_bundle_path") or "")],
        decision_refs=decision_refs,
    )
