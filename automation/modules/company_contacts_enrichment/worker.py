"""Company Contacts Enrichment main worker."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import re
import urllib.parse

from .email_validator import classify_email, deduce_department_emails
from .models import CompanyCard, EnrichmentTask
from .sources.corporate_site import crawl_corporate_site
from .sources.hh_search import search_hh_company
from .sources.people_search import search_decision_makers
from .state import CompanyEnrichmentState
from .web_research import domain_from_url, fetch_urllib_html, smart_fetch, smart_search


logger = logging.getLogger(__name__)

DOMAIN_BLACKLIST = {
    "adindex.ru",
    "bing.com",
    "career.habr.com",
    "cossa.ru",
    "duckduckgo.com",
    "facebook.com",
    "google.com",
    "instagram.com",
    "linkedin.com",
    "rutube.ru",
    "sostav.ru",
    "t.me",
    "tiktok.com",
    "twitter.com",
    "vc.ru",
    "vk.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
    "zhihu.com",
}

URL_PATH_BLACKLIST_KEYWORDS = (
    "/article/",
    "/articles/",
    "/blog/",
    "/forum/",
    "/news/",
    "/post/",
    "/posts/",
    "/question/",
    "/questions/",
    "/tag/",
    "/tags/",
    "/thread/",
    "/threads/",
    "/wiki/",
)


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in value.strip().lower()) or "unknown"


def _normalize_text(value: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", " ", (value or "").casefold()).strip()


def _extract_name_tokens(values: list[str]) -> tuple[list[str], set[str]]:
    phrases: list[str] = []
    tokens: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        phrases.append(normalized)
        for token in normalized.split():
            if len(token) >= 3:
                tokens.add(token)
    return phrases, tokens


def _extract_domain_hints(values: list[str]) -> list[str]:
    hints: list[str] = []
    for value in values:
        raw = str(value or "").strip()
        if not raw:
            continue
        candidate = raw
        if "://" not in candidate and "." in candidate and "/" not in candidate:
            candidate = f"https://{candidate}"
        domain = domain_from_url(candidate)
        if domain and domain not in hints and not _is_blacklisted_domain(domain):
            hints.append(domain)
    return hints


def _is_blacklisted_domain(domain: str) -> bool:
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in DOMAIN_BLACKLIST)


def _is_blacklisted_url(url: str) -> bool:
    lowered = url.casefold()
    return any(keyword in lowered for keyword in URL_PATH_BLACKLIST_KEYWORDS)


def _looks_like_corporate_domain(domain: str) -> bool:
    if not domain or _is_blacklisted_domain(domain):
        return False
    parts = domain.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1]
    return 2 <= len(tld) <= 6


def _domain_match_score(
    url: str,
    domain: str,
    domain_hints: list[str],
    name_phrases: list[str],
    name_tokens: set[str],
    title: str,
    snippet: str,
) -> int:
    if not domain or _is_blacklisted_domain(domain) or _is_blacklisted_url(url) or not _looks_like_corporate_domain(domain):
        return -1000

    score = 0
    matches_hint = any(domain == hint or domain.endswith(f".{hint}") or hint.endswith(f".{domain}") for hint in domain_hints)
    if matches_hint:
        score += 140
    elif domain_hints:
        return -500

    root_text = _normalize_text(domain.replace(".", " ").replace("-", " "))
    score += 12 * min(3, sum(1 for token in name_tokens if token in root_text))

    combined = _normalize_text(f"{title} {snippet}")
    score += 22 * min(2, sum(1 for phrase in name_phrases if phrase and phrase in combined))

    if "официальный сайт" in combined or "official site" in combined:
        score += 12
    if any(keyword in combined for keyword in ("контакты", "contact", "about", "о компании", "company")):
        score += 5

    parsed = urllib.parse.urlparse(url)
    path_depth = len([part for part in parsed.path.split("/") if part])
    if path_depth == 0:
        score += 8
    elif path_depth > 3:
        score -= 10

    return score


def _try_confirm_hint_domain(domain: str, *, use_firecrawl: bool) -> str:
    candidates = [f"https://{domain}"]
    if not domain.startswith("www."):
        candidates.append(f"https://www.{domain}")
    for candidate in candidates:
        content = smart_fetch(candidate, use_firecrawl=use_firecrawl)
        if content:
            return candidate
        html = fetch_urllib_html(candidate)
        if html:
            return candidate
    return ""


def _email_matches_company_domain(email: str, domain: str) -> bool:
    if "@" not in email or not domain:
        return False
    email_domain = email.split("@", 1)[1].lower()
    return email_domain == domain or email_domain.endswith(f".{domain}")


def _phone_looks_plausible(phone: str) -> bool:
    digits = phone[1:] if phone.startswith("+") else phone
    if not digits.isdigit():
        return False
    if phone.startswith("+"):
        return 10 <= len(digits) <= 15
    return len(digits) == 11 and digits.startswith(("7", "8"))


def _choose_website(task: EnrichmentTask, *, use_firecrawl: bool) -> tuple[str, str, bool]:
    names = [task.company_name] + list(task.aliases)
    domain_hints = _extract_domain_hints(names)
    name_phrases, name_tokens = _extract_name_tokens(names)

    for domain_hint in domain_hints:
        confirmed_url = _try_confirm_hint_domain(domain_hint, use_firecrawl=use_firecrawl)
        if confirmed_url:
            return confirmed_url, domain_hint, True

    # Explicit domains from the curated input list are treated as authoritative
    # even when homepage fetch is blocked. This is still safe because random
    # external domains never enter domain_hints: only explicit domain-like aliases do.
    if domain_hints:
        return f"https://{domain_hints[0]}", domain_hints[0], True

    query_parts = [f'"{task.company_name}"', "официальный сайт"]
    results = smart_search(" ".join(query_parts), limit=8, use_firecrawl=use_firecrawl)

    best_url = ""
    best_domain = ""
    best_score = -1000
    best_confirmed = False

    for item in results:
        url = str(item.get("url") or "")
        title = str(item.get("title") or "")
        snippet = str(item.get("snippet") or "")
        domain = domain_from_url(url)
        score = _domain_match_score(url, domain, domain_hints, name_phrases, name_tokens, title, snippet)
        if score > best_score:
            best_score = score
            best_url = url
            best_domain = domain
            best_confirmed = score >= (100 if domain_hints else 55)

    if best_confirmed and best_domain:
        normalized_url = best_url if best_url.startswith(("http://", "https://")) else f"https://{best_domain}"
        return normalized_url, best_domain, True

    return "", "", False


def _step_1_resolve_domain(task: EnrichmentTask, card: CompanyCard, *, use_firecrawl: bool = True) -> None:
    """Find official website domain and basic company info."""
    website, domain, confirmed = _choose_website(task, use_firecrawl=use_firecrawl)
    if website and domain:
        card.website = website
        card.website_domain = domain
        card.website_confirmed = confirmed
        card.sources.append(website)
    else:
        card.errors.append("Step 1: official website not confidently resolved")

    rusprofile_query = f'site:rusprofile.ru "{task.company_name}"'
    rp_results = smart_search(rusprofile_query, limit=2, use_firecrawl=use_firecrawl)
    for item in rp_results:
        url = str(item.get("url") or "")
        if "rusprofile.ru" not in url:
            continue
        card.rusprofile_url = url
        snippet = str(item.get("snippet") or "")
        inn_match = re.search(r"ИНН\s*[:.]?\s*(\d{10,12})", snippet)
        if inn_match:
            card.inn = inn_match.group(1)
        ceo_match = re.search(
            r"(?:генеральный директор|руководитель|директор)\s*[:\-\u2014]?\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
            snippet,
            re.IGNORECASE,
        )
        if ceo_match:
            card.ceo_name = ceo_match.group(1).strip()
        card.sources.append(url)
        break


def _step_2_crawl_site(task: EnrichmentTask, card: CompanyCard, *, use_firecrawl: bool = True) -> None:
    """Deep crawl the corporate website for contacts."""
    if not card.website or not card.website_confirmed:
        card.errors.append("Step 2 skipped: no confirmed website from Step 1")
        return

    result = crawl_corporate_site(card.website, use_firecrawl=use_firecrawl)

    for email in result.emails:
        if not _email_matches_company_domain(email, card.website_domain):
            continue
        category = classify_email(email)
        if category == "pr":
            card.pr_emails.append(email)
        elif category == "marketing":
            card.marketing_emails.append(email)
        elif category == "partnership":
            card.partnership_emails.append(email)
        else:
            card.general_emails.append(email)
        if email not in card.all_emails:
            card.all_emails.append(email)

    card.phones.extend(phone for phone in result.phones if _phone_looks_plausible(phone))
    if result.telegrams:
        card.telegram = result.telegrams[0]

    for person in result.named_contacts:
        if not any(dm.full_name == person.full_name for dm in card.decision_makers):
            card.decision_makers.append(person)

    card.sources.extend(result.pages_crawled)


def _step_3_hh_search(task: EnrichmentTask, card: CompanyCard, *, use_firecrawl: bool = True) -> None:
    result = search_hh_company(task.company_name, aliases=task.aliases, use_firecrawl=use_firecrawl)

    card.hh_employer_url = result.employer_url
    card.hh_active_marketing_vacancies = result.marketing_vacancies_count

    if result.hr_contacts:
        first_hr = result.hr_contacts[0]
        card.hh_hr_contact_name = first_hr.full_name
        card.hh_hr_contact_email = first_hr.email
        card.hh_hr_contact_phone = first_hr.phone

    for hr in result.hr_contacts:
        if not any(dm.full_name == hr.full_name for dm in card.decision_makers):
            card.decision_makers.append(hr)

    if result.employer_url:
        card.sources.append(result.employer_url)

    if result.errors:
        card.errors.extend(result.errors)


def _step_4_people_search(task: EnrichmentTask, card: CompanyCard, *, use_firecrawl: bool = True) -> None:
    result = search_decision_makers(task.company_name, aliases=task.aliases, use_firecrawl=use_firecrawl)

    if result.owner_name and not card.ceo_name:
        card.ceo_name = result.owner_name

    for person in result.decision_makers:
        if not any(dm.full_name == person.full_name for dm in card.decision_makers):
            card.decision_makers.append(person)

    if result.errors:
        card.errors.extend(result.errors)


def _step_5_llm_synthesis(task: EnrichmentTask, card: CompanyCard) -> None:
    if card.pr_emails:
        card.recommended_entry_route = f"PR email: {card.pr_emails[0]}"
    elif card.marketing_emails:
        card.recommended_entry_route = f"Marketing email: {card.marketing_emails[0]}"
    elif card.partnership_emails:
        card.recommended_entry_route = f"Partnership email: {card.partnership_emails[0]}"
    elif card.general_emails:
        card.recommended_entry_route = f"General email: {card.general_emails[0]}"
    elif card.phones:
        card.recommended_entry_route = f"Phone: {card.phones[0]} (call reception and ask for marketing/PR)"
    elif card.hh_hr_contact_email:
        card.recommended_entry_route = f"HR contact from HH.ru: {card.hh_hr_contact_email}"
    elif any(dm.department in ("PR", "Marketing", "Leadership") for dm in card.decision_makers):
        relevant = [dm for dm in card.decision_makers if dm.department in ("PR", "Marketing", "Leadership")]
        card.recommended_entry_route = f"Named contact: {relevant[0].full_name} ({relevant[0].position})"
    elif not card.website_confirmed:
        card.recommended_entry_route = "Manual review required: official website not confirmed"
    else:
        card.recommended_entry_route = "No direct contacts found. Try website contact form or manual outreach."

    sector_pitches = {
        "telecom": "Telecom brands need premium video content for product launches and brand campaigns. NSX case: MTS campaign.",
        "banking": "Banks invest heavily in brand video and internal communications. NSX's cinematic quality stands out.",
        "retail": "Retail brands need seasonal campaigns, product showcases, and brand films. NSX cases: Coffeemania, Snezhnaya Koroleva.",
        "fmcg": "FMCG brands need high-volume ad creative and brand storytelling. NSX cases: Hugo, Dior.",
        "tech": "Tech companies need product demos, corporate films, and event coverage. NSX cases: Honor, OMODA.",
        "e-commerce": "E-commerce needs product videos, brand campaigns, and scalable commercial content.",
        "aviation": "Airlines and transport need brand films and campaign video. NSX case: Aeroflot.",
        "auto_dealer": "Auto brands need cinematic commercials and dealer content. NSX cases: OMODA, Jetour, Changan.",
        "health": "Healthcare brands need trust-building content and corporate films.",
        "energy": "Energy companies need corporate films, CSR content, and internal communications.",
        "carsharing": "Mobility brands need dynamic lifestyle content and app promos.",
        "food_qsr": "QSR brands need constant ad creative and strong brand storytelling.",
    }
    card.pitch_angle = sector_pitches.get(task.sector, "NSX Production offers premium video production with proven cases for major Russian brands.")
    card.company_video_needs = f"Sector: {task.sector}. Company likely needs video content for marketing and communications."

    contact_count = len(card.pr_emails) + len(card.marketing_emails) + len(card.partnership_emails)
    dm_count = len([dm for dm in card.decision_makers if dm.department in ("PR", "Marketing", "Leadership")])
    if contact_count >= 2 and dm_count >= 1 and card.website_confirmed:
        card.confidence = 0.9
    elif contact_count >= 1 and card.website_confirmed:
        card.confidence = 0.7
    elif (card.general_emails or card.phones) and card.website_confirmed:
        card.confidence = 0.5
    elif card.decision_makers or card.hh_hr_contact_email:
        card.confidence = 0.4
    else:
        card.confidence = 0.2


def _step_6_validate_emails(task: EnrichmentTask, card: CompanyCard) -> None:
    if not card.website_domain or not card.website_confirmed:
        return

    domain = card.website_domain
    known_on_domain = [email for email in card.all_emails if _email_matches_company_domain(email, domain)]
    if not known_on_domain:
        return

    deduced = deduce_department_emails(known_on_domain[0], validate=False)
    for item in deduced:
        email = item["email"]
        if email in card.all_emails:
            continue
        card.deduced_emails.append(email)
        card.all_emails.append(email)
        category = classify_email(email)
        if category == "pr" and email not in card.pr_emails:
            card.pr_emails.append(email)
        elif category == "marketing" and email not in card.marketing_emails:
            card.marketing_emails.append(email)
        elif category == "partnership" and email not in card.partnership_emails:
            card.partnership_emails.append(email)

    card.pr_emails = list(dict.fromkeys(card.pr_emails))
    card.marketing_emails = list(dict.fromkeys(card.marketing_emails))
    card.partnership_emails = list(dict.fromkeys(card.partnership_emails))
    card.general_emails = list(dict.fromkeys(card.general_emails))
    card.deduced_emails = list(dict.fromkeys(card.deduced_emails))
    card.all_emails = list(dict.fromkeys(card.all_emails))
    card.phones = list(dict.fromkeys(card.phones))


def _write_company_card(output_dir: Path, card: CompanyCard) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "company_card.json"
    payload = asdict(card)
    payload["decision_makers"] = [asdict(dm) for dm in card.decision_makers]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = output_dir / "company_card.md"
    dm_lines = []
    for dm in card.decision_makers:
        parts = [f"**{dm.full_name}**"]
        if dm.position:
            parts.append(f"({dm.position})")
        if dm.department:
            parts.append(f"[{dm.department}]")
        if dm.email:
            parts.append(f"email: {dm.email}")
        if dm.phone:
            parts.append(f"tel: {dm.phone}")
        if dm.telegram:
            parts.append(f"tg: {dm.telegram}")
        if dm.instagram:
            parts.append(f"ig: {dm.instagram}")
        dm_lines.append("  - " + " | ".join(parts))

    deduced_note = ""
    if card.deduced_emails:
        deduced_note = f"\n- Deduced (unverified): {', '.join(card.deduced_emails)}"

    lines = [
        f"# {card.company_name}",
        "",
        "## Identity",
        f"- Website: {card.website or 'not found'}",
        f"- Domain: {card.website_domain or 'not found'}",
        f"- Website confirmed: {'yes' if card.website_confirmed else 'no'}",
        f"- Legal entity: {card.legal_entity or 'not found'}",
        f"- INN: {card.inn or 'not found'}",
        f"- CEO: {card.ceo_name or 'not found'}",
        f"- Industry: {card.industry or 'unknown'}",
        f"- Rusprofile: {card.rusprofile_url or 'not found'}",
        "",
        "## Contacts",
        f"- PR emails: {', '.join(card.pr_emails) or 'none'}",
        f"- Marketing emails: {', '.join(card.marketing_emails) or 'none'}",
        f"- Partnership emails: {', '.join(card.partnership_emails) or 'none'}",
        f"- General emails: {', '.join(card.general_emails) or 'none'}",
        f"- Phones: {', '.join(card.phones) or 'none'}",
        f"- Telegram: {card.telegram or 'none'}",
        f"- Instagram: {card.instagram or 'none'}",
        deduced_note,
        "",
        "## Decision Makers",
        *(dm_lines or ["  - none found"]),
        "",
        "## HH.ru Intelligence",
        f"- Employer page: {card.hh_employer_url or 'not found'}",
        f"- Marketing vacancies: {card.hh_active_marketing_vacancies}",
        f"- HR contact: {card.hh_hr_contact_name or 'none'} ({card.hh_hr_contact_email or 'no email'})",
        "",
        "## Recommendation",
        f"- Entry route: {card.recommended_entry_route}",
        f"- Pitch angle: {card.pitch_angle}",
        f"- Confidence: {card.confidence:.0%}",
        "",
        "## Enrichment",
        f"- Steps completed: {card.enrichment_steps_completed}",
        f"- Sources: {len(card.sources)} pages",
        f"- Last updated: {card.last_updated}",
        "",
        *(f"- Error: {error}" for error in card.errors),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return json_path, md_path


def enrich_company(project_root: Path, task: EnrichmentTask, *, use_firecrawl: bool = True) -> CompanyCard:
    card = CompanyCard(company_name=task.company_name, company_name_aliases=list(task.aliases), industry=task.sector)
    slug = _slug(task.company_name)
    state_path = project_root / "automation" / "state" / "company_enrichment_state.json"
    state = CompanyEnrichmentState.load(state_path)
    state.in_progress = slug

    output_dir = project_root / "output" / "company_contacts_enrichment" / slug

    steps = {
        1: ("Domain Resolution", lambda: _step_1_resolve_domain(task, card, use_firecrawl=use_firecrawl)),
        2: ("Corporate Site Crawl", lambda: _step_2_crawl_site(task, card, use_firecrawl=use_firecrawl)),
        3: ("HH.ru Intelligence", lambda: _step_3_hh_search(task, card, use_firecrawl=use_firecrawl)),
        4: ("People Search", lambda: _step_4_people_search(task, card, use_firecrawl=use_firecrawl)),
        5: ("LLM Synthesis", lambda: _step_5_llm_synthesis(task, card)),
        6: ("Email Validation", lambda: _step_6_validate_emails(task, card)),
    }

    for step_num in task.steps_to_run:
        if step_num not in steps:
            continue
        step_name, step_fn = steps[step_num]
        try:
            logger.info("Step %d (%s) for %s...", step_num, step_name, task.company_name)
            step_fn()
            card.enrichment_steps_completed.append(step_num)
            card.enrichment_level = max(card.enrichment_level, step_num)
            state.mark_step_done(slug, step_num)
        except Exception as exc:
            error_msg = f"Step {step_num} ({step_name}) failed: {exc}"
            logger.warning(error_msg)
            card.errors.append(error_msg)
            state.mark_step_failed(slug, step_num, str(exc))

    card.last_updated = datetime.now(timezone.utc).isoformat()
    _write_company_card(output_dir, card)

    state.mark_completed(slug)
    state.save(state_path)

    logger.info(
        "Enrichment complete for %s: %d emails, %d phones, %d decision-makers, confidence=%.0f%%",
        task.company_name,
        len(card.all_emails),
        len(card.phones),
        len(card.decision_makers),
        card.confidence * 100,
    )
    return card
