from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
import urllib.parse

from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso
from automation.modules.instagram_brand_search.recipe import extract_followers_count
from automation.policies import load_farida_policy

from .state import BrandIntelligenceState
from .web_research import run_brand_web_research, write_research_report


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\-\s\(\)]{7,}\d)")
TELEGRAM_RE = re.compile(r"https?://t\.me/[A-Za-z0-9_]+", re.IGNORECASE)
WHATSAPP_RE = re.compile(r"(?:https?://wa\.me/\d+|https?://api\.whatsapp\.com/[^\s\"'>]+)", re.IGNORECASE)
SOCIAL_DOMAINS = (
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "pinterest.com",
)


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


def _extract_brand_followers(snapshot: dict) -> tuple[int, str]:
    followers_text = str(snapshot.get("followers_text") or "").strip()
    bio = str(snapshot.get("bio") or "").strip()
    posts_text = str(snapshot.get("posts_text") or "").strip()
    count = extract_followers_count(followers_text, bio, posts_text)
    profile_counts = _extract_instagram_profile_counts(snapshot)
    if count > 0:
        parts = [f"{count:,} followers".replace(",", " ")]
        if profile_counts["following"] > 0:
            parts.append(f"{profile_counts['following']:,} following".replace(",", " "))
        if profile_counts["posts"] > 0:
            parts.append(f"{profile_counts['posts']:,} posts".replace(",", " "))
        return count, " / ".join(parts)
    fallback_text = followers_text or bio or posts_text
    return count, fallback_text[:240]


def _parse_compact_count(raw_value: str) -> int:
    text = str(raw_value or "").strip().replace(",", "").replace(" ", "")
    if not text:
        return 0
    multiplier = 1
    if text[-1:].lower() == "k":
        multiplier = 1_000
        text = text[:-1]
    elif text[-1:].lower() == "m":
        multiplier = 1_000_000
        text = text[:-1]
    elif text[-1:].lower() == "b":
        multiplier = 1_000_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def _extract_profile_count(text: str, label: str) -> int:
    match = re.search(rf"([0-9][0-9.,KMkmBb]*)\s+{label}", text or "", re.IGNORECASE)
    return _parse_compact_count(match.group(1)) if match else 0


def _extract_instagram_profile_counts(snapshot: dict) -> dict:
    raw = str(snapshot.get("followers_text") or snapshot.get("bio") or snapshot.get("posts_text") or "")
    return {
        "followers": extract_followers_count(raw, raw, raw),
        "following": _extract_profile_count(raw, "Following"),
        "posts": _extract_profile_count(raw, "Posts"),
        "raw_text": raw,
    }


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) < 7:
        return ""
    if value.strip().startswith("+"):
        return "+" + digits
    return digits


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _domain_from_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlparse(str(value or "").strip())
    except Exception:
        return ""
    return parsed.netloc.lower().removeprefix("www.")


def _is_social_domain(domain: str) -> bool:
    return any(domain == item or domain.endswith(f".{item}") for item in SOCIAL_DOMAINS)


def _brand_tokens(snapshot: dict) -> set[str]:
    tokens: set[str] = set()
    for raw_value in (
        str(snapshot.get("handle") or ""),
        str(snapshot.get("display_name") or ""),
        str(snapshot.get("_canonical_handle") or ""),
    ):
        for token in re.findall(r"[A-Za-zА-Яа-я0-9]{3,}", raw_value):
            lowered = token.lower()
            if lowered not in {"official", "brand", "shop", "store", "premium", "womenswear"}:
                tokens.add(lowered)
    return tokens


def _trusted_contact_domains(snapshot: dict, research_report) -> set[str]:
    tokens = _brand_tokens(snapshot)
    trusted: set[str] = set()

    external_link = str(snapshot.get("external_link") or "").strip()
    external_domain = _domain_from_url(external_link)
    if external_domain and not _is_social_domain(external_domain):
        trusted.add(external_domain)

    for result in research_report.search_results:
        domain = _domain_from_url(result.url)
        if not domain or _is_social_domain(domain):
            continue
        domain_tokens = set(re.findall(r"[a-z0-9а-я]{3,}", domain))
        if tokens and any(token in domain_tokens or token in domain for token in tokens if len(token) >= 4):
            trusted.add(domain)

    return trusted


def _select_primary_site_url(snapshot: dict, research_report) -> str:
    external_link = str(snapshot.get("external_link") or "").strip()
    external_domain = _domain_from_url(external_link)
    if external_link and external_domain and not _is_social_domain(external_domain):
        return external_link

    trusted_domains = _trusted_contact_domains(snapshot, research_report)
    for item in research_report.search_results:
        domain = _domain_from_url(item.url)
        if domain and domain in trusted_domains:
            return str(item.url or "").strip()
    for item in research_report.page_summaries:
        domain = _domain_from_url(item.url)
        if domain and domain in trusted_domains:
            return str(item.url or "").strip()
    return ""


def _extract_contacts(snapshot: dict, research_report) -> dict:
    trusted_domains = _trusted_contact_domains(snapshot, research_report)
    text_parts = [
        str(snapshot.get("bio") or ""),
        str(snapshot.get("external_link") or ""),
    ]
    if trusted_domains:
        text_parts.extend(
            f"{item.title} {item.snippet} {item.url}"
            for item in research_report.search_results
            if _domain_from_url(item.url) in trusted_domains
        )
        text_parts.extend(
            f"{item.title} {item.meta_description} {item.excerpt} {item.url}"
            for item in research_report.page_summaries
            if _domain_from_url(item.url) in trusted_domains
        )
    combined = "\n".join(text_parts)

    emails = _dedupe([match.group(0).lower() for match in EMAIL_RE.finditer(combined)])
    phones = _dedupe(
        [
            normalized
            for normalized in (_normalize_phone(match.group(0)) for match in PHONE_RE.finditer(combined))
            if normalized and 7 <= len(normalized.lstrip("+")) <= 15
        ]
    )
    telegrams = _dedupe([match.group(0) for match in TELEGRAM_RE.finditer(combined)])
    whatsapps = _dedupe([match.group(0) for match in WHATSAPP_RE.finditer(combined)])

    urls = []
    external_link = str(snapshot.get("external_link") or "").strip()
    if external_link:
        urls.append(external_link)
    urls.extend(
        str(item.url or "").strip()
        for item in research_report.search_results
        if _domain_from_url(item.url) in trusted_domains
    )
    urls.extend(
        str(item.url or "").strip()
        for item in research_report.page_summaries
        if _domain_from_url(item.url) in trusted_domains
    )
    contact_urls = _dedupe(
        [
            url
            for url in urls
            if url and any(keyword in url.lower() for keyword in ("contact", "support", "help", "press", "partnership", "wholesale"))
        ]
    )
    contact_urls = sorted(
        contact_urls,
        key=lambda item: (
            len([part for part in urllib.parse.urlparse(item).path.split("/") if part]),
            len(item),
        ),
    )[:3]

    preferred_channel = "instagram_dm"
    if emails:
        preferred_channel = "email"
    elif contact_urls:
        preferred_channel = "website_contact"

    return {
        "emails": emails,
        "phones": phones,
        "telegrams": telegrams,
        "whatsapps": whatsapps,
        "contact_urls": contact_urls,
        "preferred_contact_channel": preferred_channel,
        "contact_count": len(emails) + len(phones) + len(telegrams) + len(whatsapps) + len(contact_urls),
    }


def _load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_brand_dossier(
    project_root: Path,
    *,
    handle: str,
    snapshot: dict,
    source_bloggers: list[str],
    supporting_stats: dict,
    research_report,
    contact_signals: dict,
    evidence_dir: Path,
) -> tuple[Path, Path]:
    slug = _slug(handle)
    arbiter_packet = _load_optional_json(project_root / "output" / "brand_arbiter" / slug / "intelligence_packet.json")
    profile_counts = _extract_instagram_profile_counts(snapshot)
    primary_site_url = _select_primary_site_url(snapshot, research_report)

    dossier_payload = {
        "brand_handle": handle,
        "brand_name": str(snapshot.get("display_name") or handle),
        "profile_url": str(snapshot.get("profile_url") or ""),
        "external_link": str(snapshot.get("external_link") or ""),
        "primary_site_url": primary_site_url,
        "account_kind": str(snapshot.get("account_kind") or ""),
        "category_label": str(snapshot.get("category_label") or ""),
        "niche": str(snapshot.get("niche") or ""),
        "instagram_profile": profile_counts,
        "source_bloggers": source_bloggers,
        "source_posts_count": int(supporting_stats.get("source_posts_count") or 0),
        "recent_mentions_30d": int(supporting_stats.get("recent_mentions_30d") or 0),
        "recent_mentions_90d": int(supporting_stats.get("recent_mentions_90d") or 0),
        "official_site_found": bool(research_report.official_site_found),
        "web_tone": str(research_report.tone or ""),
        "geo_hint": str(research_report.geo or ""),
        "price_segment": str(research_report.price_segment or ""),
        "review_source_count": int(research_report.review_source_count or 0),
        "contact_signals": contact_signals,
        "top_search_results": [
            {"title": item.title, "url": item.url, "snippet": item.snippet}
            for item in research_report.search_results[:5]
        ],
        "arbiter_recommendation": {
            "verdict": str(arbiter_packet.get("verdict") or ""),
            "recommended_action": str(arbiter_packet.get("recommended_action") or ""),
            "recommended_channel": str(arbiter_packet.get("recommended_channel") or ""),
            "confidence": str(arbiter_packet.get("confidence") or ""),
            "segment": str(arbiter_packet.get("brand_outreach_segment") or ""),
            "special_handling": str(arbiter_packet.get("special_handling") or ""),
        },
    }

    missing_items: list[str] = []
    if not research_report.official_site_found:
        missing_items.append("official_site")
    if not any(contact_signals.get(key) for key in ("emails", "phones", "telegrams", "whatsapps", "contact_urls")):
        missing_items.append("contacts")
    if not research_report.review_source_count:
        missing_items.append("reviews")
    dossier_payload["missing_items"] = missing_items

    dossier_json_path = evidence_dir / "brand_dossier.json"
    dossier_md_path = evidence_dir / "brand_dossier.md"
    dossier_json_path.write_text(json.dumps(dossier_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    contact_lines = []
    for key in ("emails", "phones", "telegrams", "whatsapps", "contact_urls"):
        values = list(contact_signals.get(key) or [])
        if values:
            contact_lines.append(f"- {key}: {', '.join(values)}")
    if not contact_lines:
        contact_lines.append("- contacts: not found")

    recommendation_lines = [
        f"- verdict: {dossier_payload['arbiter_recommendation']['verdict'] or 'not generated'}",
        f"- recommended_action: {dossier_payload['arbiter_recommendation']['recommended_action'] or 'not generated'}",
        f"- recommended_channel: {dossier_payload['arbiter_recommendation']['recommended_channel'] or 'not generated'}",
        f"- segment: {dossier_payload['arbiter_recommendation']['segment'] or supporting_stats.get('brand_value_tier') or 'unknown'}",
        f"- special_handling: {dossier_payload['arbiter_recommendation']['special_handling'] or supporting_stats.get('special_handling') or 'none'}",
    ]

    dossier_lines = [
        f"# Brand Dossier @{handle}",
        "",
        "## Profile",
        f"- Brand name: {dossier_payload['brand_name']}",
        f"- Profile URL: {dossier_payload['profile_url'] or 'not found'}",
        f"- External link: {dossier_payload['external_link'] or 'not found'}",
        f"- Primary site: {dossier_payload['primary_site_url'] or 'not found'}",
        f"- Account kind: {dossier_payload['account_kind'] or 'unknown'}",
        f"- Category label: {dossier_payload['category_label'] or 'unknown'}",
        f"- Niche: {dossier_payload['niche'] or 'unknown'}",
        "",
        "## Instagram Stats",
        f"- Followers: {profile_counts['followers']:,}".replace(",", " "),
        f"- Following: {profile_counts['following']:,}".replace(",", " "),
        f"- Posts: {profile_counts['posts']:,}".replace(",", " "),
        "",
        "## Source Context",
        f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
        f"- Source posts count: {supporting_stats.get('source_posts_count', 0)}",
        f"- Recent mentions 30d: {supporting_stats.get('recent_mentions_30d', 0)}",
        f"- Recent mentions 90d: {supporting_stats.get('recent_mentions_90d', 0)}",
        "",
        "## Web Presence",
        f"- Official site found: {'yes' if research_report.official_site_found else 'no'}",
        f"- Web tone: {research_report.tone}",
        f"- Geo hint: {research_report.geo}",
        f"- Price segment: {research_report.price_segment}",
        f"- Review source count: {research_report.review_source_count}",
        "",
        "## Contacts",
        *contact_lines,
        f"- preferred_contact_channel: {contact_signals.get('preferred_contact_channel') or 'instagram_dm'}",
        "",
        "## Recommendation",
        *recommendation_lines,
        "",
        "## Missing",
        *([f"- {item}" for item in missing_items] or ["- nothing critical"]),
        "",
    ]
    dossier_md_path.write_text("\n".join(dossier_lines), encoding="utf-8-sig")
    return dossier_json_path, dossier_md_path


def _derive_supporting_stats(snapshot: dict, research_report, source_bloggers: list[str], *, policy: dict) -> dict:
    now = datetime.now(timezone.utc)
    sources = list(snapshot.get("sources") or [])
    source_dates = [_parse_datetime(source.get("post_date_iso") or "") for source in sources]
    source_dates = [item for item in source_dates if item is not None]
    recent_30d = sum(1 for item in source_dates if item >= now - timedelta(days=30))
    recent_90d = sum(1 for item in source_dates if item >= now - timedelta(days=90))
    ad_high = sum(1 for source in sources if str(source.get("ad_likelihood") or "").strip().lower() == "high")
    ad_medium = sum(1 for source in sources if str(source.get("ad_likelihood") or "").strip().lower() == "medium")
    brand_follower_count, brand_followers_text = _extract_brand_followers(snapshot)
    official_signal = 1 if research_report.official_site_found else 0
    positive_signal_count = int(research_report.positive_signal_count or 0)
    negative_signal_count = int(research_report.negative_signal_count or 0)

    if official_signal and (positive_signal_count >= 2 or len(source_bloggers) >= 2):
        brand_value_tier = "high"
    elif official_signal or positive_signal_count >= 1 or brand_follower_count >= 5000:
        brand_value_tier = "medium"
    else:
        brand_value_tier = "low"
    ultra_premium_threshold = int(policy.get("ultra_premium_policy", {}).get("follower_threshold") or 1_000_000)
    if brand_follower_count >= ultra_premium_threshold:
        brand_value_tier = "ultra_premium"

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
        "brand_follower_count": brand_follower_count,
        "brand_followers_text": brand_followers_text,
        "follower_count": brand_follower_count,
        "is_ultra_premium_brand": brand_follower_count >= ultra_premium_threshold,
        "special_handling": str(policy.get("ultra_premium_policy", {}).get("special_handling") or "") if brand_follower_count >= ultra_premium_threshold else "",
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
    policy = load_farida_policy(project_root)
    state_path = project_root / "automation" / "state" / "brand_intelligence_state.json"
    state = BrandIntelligenceState.load(state_path)
    state.current_brand_handle = handle

    source_bloggers = _load_source_bloggers(task, snapshot)
    research_report = run_brand_web_research(snapshot)
    supporting_stats = _derive_supporting_stats(snapshot, research_report, source_bloggers, policy=policy)
    contact_signals = _extract_contacts(snapshot, research_report)
    evidence_dir = project_root / "output" / "brand_intelligence" / _slug(handle)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    web_research_path = evidence_dir / "web_research.json"
    evidence_bundle_path = evidence_dir / "evidence_bundle.json"
    evidence_report_path = evidence_dir / "evidence_report.md"
    dossier_json_path = evidence_dir / "brand_dossier.json"
    dossier_md_path = evidence_dir / "brand_dossier.md"
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
        "contact_signals": contact_signals,
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
    dossier_json_path, dossier_md_path = _write_brand_dossier(
        project_root,
        handle=handle,
        snapshot=snapshot,
        source_bloggers=source_bloggers,
        supporting_stats=supporting_stats,
        research_report=research_report,
        contact_signals=contact_signals,
        evidence_dir=evidence_dir,
    )

    report_lines = [
        f"# Evidence Bundle @{handle}",
        "",
        f"- Brand name: {snapshot.get('display_name') or handle}",
        f"- Source bloggers: {', '.join(source_bloggers) or 'none'}",
        f"- Brand follower count: {supporting_stats['brand_follower_count']:,}".replace(",", " "),
        f"- Primary site: {_select_primary_site_url(snapshot, research_report) or 'not found'}",
        f"- Official site found: {'yes' if research_report.official_site_found else 'no'}",
        f"- Preferred contact channel: {contact_signals.get('preferred_contact_channel') or 'instagram_dm'}",
        f"- Review source count: {research_report.review_source_count}",
        f"- Web tone: {research_report.tone}",
        f"- Geo hint: {research_report.geo}",
        f"- Price segment: {research_report.price_segment}",
        "",
        "## Contacts",
    ]
    if any(contact_signals.get(key) for key in ("emails", "phones", "telegrams", "whatsapps", "contact_urls")):
        for key in ("emails", "phones", "telegrams", "whatsapps", "contact_urls"):
            values = list(contact_signals.get(key) or [])
            if values:
                report_lines.append(f"- {key}: {', '.join(values)}")
    else:
        report_lines.append("- contacts: not found")
    report_lines.extend(
        [
            "",
        "## Supporting Stats",
        ]
    )
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
        "dossier_json_path": str(dossier_json_path),
        "dossier_md_path": str(dossier_md_path),
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
        str(dossier_json_path),
        str(dossier_md_path),
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
                    f"- Brand dossier: {dossier_md_path.as_posix()}",
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
            "brand_dossier_json_path": str(dossier_json_path),
            "brand_dossier_md_path": str(dossier_md_path),
            "contact_signals": contact_signals,
            "supporting_stats": supporting_stats,
        },
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
    )
