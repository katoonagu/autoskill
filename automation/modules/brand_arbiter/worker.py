from __future__ import annotations

import json
from pathlib import Path

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso
from automation.llm.clients import AutoskillLLMClient, LLMUnavailableError
from automation.llm.prompts.brand_arbiter import build_brand_arbiter_prompt
from automation.llm.schemas import BRAND_ARBITER_SCHEMA
from automation.policies import load_farida_policy

from .state import BrandArbiterState


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str, *, label: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"{label} not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _normalize_list(values: list[str], fallback: str) -> list[str]:
    items = [str(item).strip() for item in values if str(item).strip()]
    return items or [fallback]


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _choose_channel(snapshot: dict, evidence_bundle: dict) -> str:
    external_link = str(snapshot.get("external_link") or "").lower()
    bio = str(snapshot.get("bio") or "").lower()
    if "mailto:" in external_link or "@" in bio or "email" in bio:
        return "email"
    if external_link and "instagram.com" not in external_link:
        return "website_contact"
    if evidence_bundle.get("source_bloggers"):
        return "instagram_dm"
    return "instagram_dm"


def _heuristic_packet(task: AgentTask, evidence_bundle: dict, media_report: dict | None, *, policy: dict) -> dict:
    snapshot = dict(evidence_bundle.get("discovery_snapshot") or {})
    stats = dict(evidence_bundle.get("mention_statistics") or {})
    derived = dict(evidence_bundle.get("derived_numeric_features") or {})
    media_present = bool(media_report)

    brand_signal = int(derived.get("brand_signal_score") or 35)
    fit_signal = int(derived.get("fit_signal_score") or 35)
    positive_signals = int(stats.get("positive_signal_count") or 0)
    negative_signals = int(stats.get("negative_signal_count") or 0)
    unique_bloggers = int(stats.get("unique_blogger_count") or 0)
    review_source_count = int(stats.get("review_source_count") or 0)
    official_site_found = bool(stats.get("official_site_found"))
    personalization_gap = bool(stats.get("personalization_gap"))
    signal_conflict = bool(stats.get("signal_conflict"))
    brand_value_tier = str(stats.get("brand_value_tier") or "low")
    brand_follower_count = int(stats.get("brand_follower_count") or stats.get("follower_count") or 0)
    ultra_premium_threshold = int(policy.get("ultra_premium_policy", {}).get("follower_threshold") or 1_000_000)
    ultra_premium_special_handling = str(policy.get("ultra_premium_policy", {}).get("special_handling") or "")
    instagram_native_policy = dict(policy.get("instagram_native_exception") or {})
    instagram_native_proxy = dict(instagram_native_policy.get("heuristic_proxy") or {})
    allowed_account_kinds = {
        str(item).strip().lower() for item in (instagram_native_proxy.get("allowed_account_kinds") or ["brand_store"])
    }
    instagram_native_min_followers = int(instagram_native_proxy.get("min_brand_follower_count") or 20_000)
    instagram_native_min_creator_mentions = int(instagram_native_proxy.get("min_creator_mentions") or 0)
    instagram_native_max_risk = int(instagram_native_proxy.get("max_risk_score") or 44)
    require_signal_conflict_false = bool(instagram_native_proxy.get("require_signal_conflict_false", True))
    account_kind = str(snapshot.get("account_kind") or "").strip().lower()

    brand_quality_score = _clamp(brand_signal + (10 if official_site_found else 0) + (positive_signals * 3) - (negative_signals * 5))
    creator_fit_score = _clamp(fit_signal + min(10, unique_bloggers * 4) + (4 if str(snapshot.get("niche") or "").strip() else 0))
    evidence_quality_score = _clamp(
        28
        + (15 if official_site_found else 0)
        + min(18, unique_bloggers * 6)
        + min(10, review_source_count * 4)
        + min(8, len(evidence_bundle.get("page_summaries") or []) * 2)
        - (12 if signal_conflict else 0)
    )
    risk_score = _clamp(
        18
        + (20 if account_kind == "service_provider" else 0)
        + (15 if str(snapshot.get("brand_likelihood") or "").strip().lower() == "low" else 0)
        + (negative_signals * 8)
        + (12 if signal_conflict else 0)
        - (8 if official_site_found else 0)
    )
    outreach_readiness_score = _clamp(
        int((brand_quality_score * 0.35) + (creator_fit_score * 0.35) + (evidence_quality_score * 0.2) + ((100 - risk_score) * 0.1))
    )

    if evidence_quality_score >= 74 and unique_bloggers >= 2:
        evidence_strength = "strong"
    elif evidence_quality_score >= 54:
        evidence_strength = "medium"
    else:
        evidence_strength = "weak"

    if evidence_quality_score >= 72 and risk_score < 45 and not signal_conflict:
        confidence = "high"
    elif evidence_quality_score >= 45 and risk_score < 65 and not signal_conflict:
        confidence = "medium"
    else:
        confidence = "low"

    instagram_native_exception = (
        bool(instagram_native_policy.get("enabled", True))
        and not official_site_found
        and account_kind in allowed_account_kinds
        and brand_follower_count >= instagram_native_min_followers
        and unique_bloggers >= instagram_native_min_creator_mentions
        and risk_score <= instagram_native_max_risk
        and (not require_signal_conflict_false or not signal_conflict)
    )

    media_enrichment_required = (
        not media_present
        and (
            ((confidence == "low" and outreach_readiness_score < 70) and not instagram_native_exception)
            or ((evidence_strength == "weak" and outreach_readiness_score < 70) and not instagram_native_exception)
            or (brand_value_tier == "high" and personalization_gap)
            or signal_conflict
        )
    )

    strict_review_required = confidence == "low" and evidence_strength == "weak" and not instagram_native_exception
    need_more_research = (evidence_strength == "weak" and outreach_readiness_score < 60) or strict_review_required

    if media_enrichment_required:
        verdict = "hold"
        recommended_action = "hold"
    elif strict_review_required or risk_score >= 60 or need_more_research:
        verdict = "validate"
        recommended_action = "validate"
    elif instagram_native_exception and risk_score <= instagram_native_max_risk and outreach_readiness_score >= 56:
        verdict = "plan_outreach"
        recommended_action = "plan_outreach"
    elif outreach_readiness_score >= 68 and confidence != "low" and evidence_strength != "weak":
        verdict = "plan_outreach"
        recommended_action = "plan_outreach"
    else:
        verdict = "hold"
        recommended_action = "validate"

    research_gaps: list[str] = []
    if not official_site_found:
        research_gaps.append("Не найден уверенный официальный сайт бренда.")
    if unique_bloggers < 2:
        research_gaps.append("Слишком мало независимых creator-сигналов по бренду.")
    if review_source_count == 0:
        research_gaps.append("Нет внешних review/reputation сигналов.")
    if personalization_gap:
        research_gaps.append("Не хватает материала для сильного персонализированного захода.")
    if signal_conflict:
        research_gaps.append("Есть конфликтующие сигналы между discovery и web evidence.")
    if media_enrichment_required:
        research_gaps.append("Нужен дополнительный media-context по постам, reels или комментариям.")
    if strict_review_required:
        research_gaps.append("Сочетание low confidence и weak evidence требует дополнительной проверки перед outreach.")
    if instagram_native_exception:
        research_gaps = [item for item in research_gaps if "официальный сайт" not in item]

    brand_strengths = []
    if official_site_found:
        brand_strengths.append("Есть сигнал официального сайта или внешнего брендового присутствия.")
    if instagram_native_exception:
        brand_strengths.append("Кейс подпадает под Instagram-native exception: сильный брендовый профиль без обязательного внешнего сайта.")
    if unique_bloggers >= 2:
        brand_strengths.append("Бренд всплывает у нескольких релевантных блогеров.")
    if positive_signals >= 2:
        brand_strengths.append("Во внешней выдаче есть коммерческие или позитивные сигналы.")
    if outreach_readiness_score >= 68 and not strict_review_required:
        brand_strengths.append("Достаточно материала, чтобы собрать правдоподобный outreach angle.")

    brand_weaknesses = []
    if not official_site_found:
        brand_weaknesses.append("Внешняя легитимность бренда подтверждена слабо.")
    if unique_bloggers <= 1:
        brand_weaknesses.append("Кейс держится на одном creator-source и слабее переносится в outreach.")
    if personalization_gap:
        brand_weaknesses.append("Не хватает конкретики для убедительного персонального оффера.")
    if evidence_strength == "weak":
        brand_weaknesses.append("Плотность evidence пока недостаточная для уверенного решения.")

    risk_flags = []
    if risk_score >= 60:
        risk_flags.append("Высокий суммарный risk_score.")
    if signal_conflict:
        risk_flags.append("Есть конфликт сигналов между discovery и web research.")
    if negative_signals >= 2:
        risk_flags.append("Во внешней выдаче заметны негативные lexical signals.")
    if account_kind == "service_provider":
        risk_flags.append("Профиль может быть не брендом, а service-provider или personal business.")
    if brand_follower_count >= ultra_premium_threshold:
        risk_flags.append("Бренд попадает в сегмент ultra_premium и может требовать отдельного продукта или отдельного трека продаж.")

    brand_outreach_segment = "ultra_premium" if brand_follower_count >= ultra_premium_threshold else brand_value_tier
    special_handling = ultra_premium_special_handling if brand_follower_count >= ultra_premium_threshold else ""

    niche = str(snapshot.get("niche") or "бренд-категории")
    creator_refs = ", ".join(evidence_bundle.get("source_bloggers") or []) or "текущего creator-сета"
    why_this_brand = (
        f"Бренд уже присутствует в релевантном creator-контексте ({creator_refs}) и показывает fit по нише {niche}."
        if unique_bloggers
        else f"Есть базовый fit по нише {niche}, но creator-context пока ограничен."
    )
    why_now = (
        "Есть свежие creator-mentions, поэтому можно опереться на актуальный контекст и recent visibility."
        if int(stats.get("recent_mentions_90d") or 0) > 0
        else "Кейс лучше использовать как аккуратный warm outreach без сильной опоры на recent momentum."
    )
    recommended_angle = (
        f"Опирайтесь на fit бренда в нише {niche}, на observed creator-context и на конкретный визуальный сценарий интеграции."
    )
    what_not_to_say = _normalize_list(
        [
            "Не утверждать, что мы уже работали с брендом, если этого не было.",
            "Не обещать KPI, охваты или продажи без отдельного подтверждения.",
            "Не ссылаться на комментарии как на доказательство качества бренда.",
            "Не давить общими фразами про идеальный fit без опоры на evidence.",
        ],
        "Не использовать непроверенные claims.",
    )

    media_notes = []
    if media_present:
        media_notes.extend(str(item).strip() for item in media_report.get("use_as_signal") or [] if str(item).strip())
    if media_notes:
        brand_strengths.extend(media_notes[:2])

    return {
        "confidence": confidence,
        "evidence_strength": evidence_strength,
        "brand_quality_score": brand_quality_score,
        "creator_fit_score": creator_fit_score,
        "outreach_readiness_score": outreach_readiness_score,
        "risk_score": risk_score,
        "evidence_quality_score": evidence_quality_score,
        "brand_strengths": _normalize_list(brand_strengths, "Есть базовый creator-context по бренду."),
        "brand_weaknesses": _normalize_list(
            brand_weaknesses,
            "Критичных слабых сторон не выявлено, но кейс остаётся рабочей гипотезой.",
        ),
        "risk_flags": _normalize_list(risk_flags, "Явных блокирующих risk-flags не найдено."),
        "why_this_brand": why_this_brand,
        "why_now": why_now,
        "what_not_to_say": what_not_to_say,
        "recommended_channel": _choose_channel(snapshot, evidence_bundle),
        "recommended_angle": recommended_angle,
        "need_more_research": need_more_research,
        "research_gaps": research_gaps,
        "media_enrichment_required": media_enrichment_required,
        "verdict": verdict,
        "recommended_action": recommended_action,
        "personalization_gap": personalization_gap,
        "signal_conflict": signal_conflict,
        "instagram_native_exception": instagram_native_exception,
        "brand_outreach_segment": brand_outreach_segment,
        "special_handling": special_handling,
    }


def _build_packet(task: AgentTask, project_root: Path, evidence_bundle: dict, media_report: dict | None, *, policy: dict) -> dict:
    client = AutoskillLLMClient.from_project_root(project_root)
    if client.is_available():
        try:
            payload = client.generate_structured(
                build_brand_arbiter_prompt(evidence_bundle=evidence_bundle, media_report=media_report, policy=policy),
                BRAND_ARBITER_SCHEMA,
                model=client.config.brain_model,
                temperature=0,
            )
            payload["llm_provider"] = client.config.provider
            return payload
        except (LLMUnavailableError, RuntimeError, ValueError):
            pass
    payload = _heuristic_packet(task, evidence_bundle, media_report, policy=policy)
    payload["llm_provider"] = "heuristic_fallback"
    return payload


def persist_brand_arbiter_result(
    project_root: Path,
    task: AgentTask,
    *,
    evidence_bundle: dict,
    packet: dict,
    media_report: dict | None,
    write_wiki: bool = True,
    custom_report_markdown: str = "",
) -> TaskResult:
    brand_handle = str(evidence_bundle.get("brand_handle") or task.entity_refs.get("brand_handle") or "")
    brand_name = str(evidence_bundle.get("brand_name") or brand_handle)
    supporting_stats = dict(packet.get("supporting_stats") or evidence_bundle.get("mention_statistics") or {})
    media_report_path = str(task.inputs.get("media_report_path") or "")
    state_path = project_root / "automation" / "state" / "brand_arbiter_state.json"
    state = BrandArbiterState.load(state_path)
    state.current_brand_handle = brand_handle

    packet["brand_handle"] = brand_handle
    packet["brand_name"] = brand_name
    packet["supporting_evidence_refs"] = [
        str(task.inputs.get("brand_snapshot_path") or ""),
        str(task.inputs.get("evidence_bundle_path") or ""),
        str(task.inputs.get("evidence_report_path") or ""),
        media_report_path,
    ]
    packet["supporting_evidence_refs"] = [item for item in packet["supporting_evidence_refs"] if item]
    packet["supporting_stats"] = supporting_stats

    packet_dir = project_root / "output" / "brand_arbiter" / _slug(brand_handle)
    packet_dir.mkdir(parents=True, exist_ok=True)
    intelligence_packet_path = packet_dir / "intelligence_packet.json"
    arbiter_report_path = packet_dir / "arbiter_report.md"
    packet["arbiter_reasoning_ref"] = str(arbiter_report_path)
    intelligence_packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    if custom_report_markdown.strip():
        arbiter_report_path.write_text(custom_report_markdown.strip() + "\n", encoding="utf-8-sig")
    else:
        criteria_lines = [
            "- Business legitimacy",
            "- Collab evidence",
            "- Creator fit",
            "- Offerability",
            "- Risk",
            "- Evidence strength",
            "- Timing / why now",
        ]
        analysis_lines = []
        for key in ("brand_strengths", "brand_weaknesses", "risk_flags", "research_gaps"):
            values = packet.get(key) or []
            if values:
                analysis_lines.append(f"### {key}")
                analysis_lines.extend(f"- {item}" for item in values)
                analysis_lines.append("")
        arbiter_report_path.write_text(
            "\n".join(
                [
                    f"# Brand Arbiter @{brand_handle}",
                    "",
                    "## State",
                    f"- Brand name: {brand_name}",
                    f"- Confidence: {packet['confidence']}",
                    f"- Evidence strength: {packet['evidence_strength']}",
                    f"- Provider: {packet['llm_provider']}",
                    f"- Media report attached: {'yes' if media_report else 'no'}",
                    f"- Instagram-native exception: {'yes' if packet.get('instagram_native_exception') else 'no'}",
                    f"- Segment: {packet.get('brand_outreach_segment') or 'unspecified'}",
                    f"- Special handling: {packet.get('special_handling') or 'none'}",
                    "",
                    "## Criteria",
                    *criteria_lines,
                    "",
                    "## Analysis",
                    *analysis_lines,
                    "## Verdict",
                    f"- Verdict: {packet['verdict']}",
                    f"- Recommended action: {packet['recommended_action']}",
                    f"- Recommended channel: {packet['recommended_channel']}",
                    f"- Recommended angle: {packet['recommended_angle']}",
                    f"- Why this brand: {packet['why_this_brand']}",
                    f"- Why now: {packet['why_now']}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )

    state.packets[brand_handle] = {
        "intelligence_packet_path": str(intelligence_packet_path),
        "verdict": packet["verdict"],
        "recommended_action": packet["recommended_action"],
    }
    state.reports[brand_handle] = {"arbiter_report_path": str(arbiter_report_path)}
    if brand_handle not in state.completed_brand_handles:
        state.completed_brand_handles.append(brand_handle)
    state.current_brand_handle = ""
    state.save(state_path)

    decision_refs: list[str] = []
    if write_wiki:
        brand_page = project_root / "knowledge" / "llm_wiki" / "brands" / f"{_slug(brand_handle)}.md"
        decision_page = project_root / "knowledge" / "llm_wiki" / "decisions" / f"brand_arbiter__{_slug(brand_handle)}.md"
        brand_page.parent.mkdir(parents=True, exist_ok=True)
        decision_page.parent.mkdir(parents=True, exist_ok=True)
        brand_page.write_text(
            "\n".join(
                [
                    f"# Brand @{brand_handle}",
                    "",
                    f"- Intelligence packet: {intelligence_packet_path.as_posix()}",
                    f"- Arbiter report: {arbiter_report_path.as_posix()}",
                    f"- Verdict: {packet['verdict']}",
                    f"- Recommended action: {packet['recommended_action']}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_page.write_text(
            "\n".join(
                [
                    f"# Decision Brand Arbiter @{brand_handle}",
                    "",
                    f"- Confidence: {packet['confidence']}",
                    f"- Verdict: {packet['verdict']}",
                    f"- Recommended action: {packet['recommended_action']}",
                    f"- Intelligence packet: {intelligence_packet_path.as_posix()}",
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
        summary=f"Arbiter verdict prepared for @{brand_handle}.",
        confidence=str(packet["confidence"]),
        outputs={
            "brand_handle": brand_handle,
            "brand_name": brand_name,
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path") or ""),
            "source_bloggers": list(evidence_bundle.get("source_bloggers") or []),
            "supporting_stats": supporting_stats,
            "intelligence_packet_path": str(intelligence_packet_path),
            "arbiter_report_path": str(arbiter_report_path),
            "recommended_action": str(packet["recommended_action"]),
            "verdict": str(packet["verdict"]),
            "confidence": str(packet["confidence"]),
            "need_more_research": "true" if _coerce_bool(packet.get("need_more_research")) else "false",
            "media_enrichment_required": "true" if _coerce_bool(packet.get("media_enrichment_required")) else "false",
            "instagram_native_exception": "true" if _coerce_bool(packet.get("instagram_native_exception")) else "false",
            "brand_outreach_segment": str(packet.get("brand_outreach_segment") or ""),
            "special_handling": str(packet.get("special_handling") or ""),
            "media_report_path": media_report_path,
        },
        evidence_refs=[str(intelligence_packet_path), str(arbiter_report_path), str(task.inputs.get("evidence_bundle_path") or ""), media_report_path],
        decision_refs=decision_refs,
    )


def run_brand_arbiter_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    if task.task_type != "brand_arbiter.evaluate_case":
        raise RuntimeError(f"Unsupported brand arbiter task type: {task.task_type}")

    evidence_bundle = _load_json(str(task.inputs.get("evidence_bundle_path") or ""), label="Evidence bundle")
    media_report_path = str(task.inputs.get("media_report_path") or "")
    media_report = _load_json(media_report_path, label="Media report") if media_report_path else None
    policy = load_farida_policy(project_root)
    packet = _build_packet(task, project_root, evidence_bundle, media_report, policy=policy)
    return persist_brand_arbiter_result(
        project_root,
        task,
        evidence_bundle=evidence_bundle,
        packet=packet,
        media_report=media_report,
        write_wiki=write_wiki,
    )
