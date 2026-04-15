"""Resolve person-first outreach routes for The Blueprint shortlist."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re
import urllib.parse

import yaml

from .sources.corporate_site import crawl_corporate_site
from .sources.people_search import search_decision_makers
from .web_research import (
    domain_from_url,
    extract_emails_from_text,
    extract_telegrams_from_text,
    smart_search,
)


INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._/%-]+", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\]\"']+", re.IGNORECASE)
SOCIAL_HOSTS = ("instagram.com", "t.me", "telegram.me")
NOISE_DOMAINS = (
    "theblueprint.ru",
    "vc.ru",
    "cossa.ru",
    "sostav.ru",
    "adindex.ru",
    "forbes.ru",
    "rbc.ru",
    "vedomosti.ru",
    "moskvichmag.ru",
    "the-village.ru",
    "youtube.com",
    "youtu.be",
    "behance.net",
)


def _normalize_brand_key(value: str) -> str:
    return " ".join(str(value or "").replace("’", "'").replace("`", "'").replace("ё", "е").casefold().split())


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _extract_instagrams(text: str) -> list[str]:
    return _unique_strings(match.group(0).rstrip("/,.;)") for match in INSTAGRAM_URL_RE.finditer(text or ""))


def _extract_urls(text: str) -> list[str]:
    return _unique_strings(match.group(0).rstrip("/,.;)") for match in URL_RE.finditer(text or ""))


def _extract_person_names_from_company(company: dict) -> list[str]:
    names: list[str] = []
    contacts = company.get("contacts") or {}
    names.extend(_listify(contacts.get("known_founders")))
    names.extend(_listify(contacts.get("founders")))
    if contacts.get("new_pr_director"):
        names.append(contacts.get("new_pr_director"))
    for item in _listify(company.get("hiring")):
        if isinstance(item, dict) and item.get("hired_person"):
            names.append(item.get("hired_person"))
    cleaned = []
    for name in names:
        value = " ".join(str(name or "").split())
        if len(value) >= 4:
            cleaned.append(value)
    return _unique_strings(cleaned)


def _preferred_website(company: dict) -> str:
    contacts = company.get("contacts") or {}
    website = str(contacts.get("website") or "").strip()
    if website and not website.startswith("http"):
        website = f"https://{website}"
    return website


def _status_for_resolution(person_instagrams: list[str], person_telegrams: list[str], named_emails: list[str], brand_instagrams: list[str], brand_telegrams: list[str]) -> tuple[str, str]:
    if person_instagrams or person_telegrams:
        return "resolved_person_route", "high"
    if named_emails and (brand_instagrams or brand_telegrams):
        return "resolved_brand_route", "medium"
    if named_emails or brand_instagrams or brand_telegrams:
        return "partial", "low"
    return "unresolved", "low"


def _search_query_results(query: str, *, limit: int = 5) -> list[dict]:
    try:
        return smart_search(query, limit=limit, use_firecrawl=False)
    except Exception:
        return []


def _search_person_socials(company_name: str, person_name: str) -> dict:
    instagram_urls: list[str] = []
    telegram_urls: list[str] = []
    proof_urls: list[str] = []
    emails: list[str] = []
    search_queries_used: list[str] = []

    queries = [
        f'site:instagram.com "{person_name}" "{company_name}"',
        f'site:t.me "{person_name}" "{company_name}"',
        f'"{person_name}" "{company_name}" Instagram',
        f'"{person_name}" "{company_name}" Telegram',
    ]

    for query in queries:
        search_queries_used.append(query)
        for item in _search_query_results(query, limit=4):
            url = str(item.get("url") or "")
            snippet = f"{item.get('title') or ''} {item.get('snippet') or ''}"
            proof_urls.append(url)
            instagram_urls.extend(_extract_instagrams(f"{url} {snippet}"))
            telegram_urls.extend(extract_telegrams_from_text(f"{url} {snippet}"))
            emails.extend(extract_emails_from_text(snippet))

    return {
        "instagram_urls": _unique_strings(instagram_urls),
        "telegram_urls": _unique_strings(telegram_urls),
        "emails": _unique_strings(emails),
        "proof_urls": _unique_strings(proof_urls),
        "search_queries_used": search_queries_used,
    }


def _search_brand_socials(company_name: str, aliases: list[str]) -> dict:
    brand_instagrams: list[str] = []
    brand_telegrams: list[str] = []
    websites: list[str] = []
    proof_urls: list[str] = []
    search_queries_used: list[str] = []

    base_name = aliases[0] if aliases else company_name
    queries = [
        f'site:instagram.com "{base_name}"',
        f'site:t.me "{base_name}"',
        f'"{base_name}" официальный сайт',
    ]

    for query in queries:
        search_queries_used.append(query)
        for item in _search_query_results(query, limit=4):
            url = str(item.get("url") or "")
            snippet = f"{item.get('title') or ''} {item.get('snippet') or ''}"
            proof_urls.append(url)
            brand_instagrams.extend(_extract_instagrams(f"{url} {snippet}"))
            brand_telegrams.extend(extract_telegrams_from_text(f"{url} {snippet}"))
            for candidate in _extract_urls(f"{url} {snippet}"):
                domain = domain_from_url(candidate)
                if domain and not any(host in domain for host in SOCIAL_HOSTS) and not any(noise in domain for noise in NOISE_DOMAINS):
                    websites.append(candidate)

    return {
        "brand_instagrams": _unique_strings(brand_instagrams),
        "brand_telegrams": _unique_strings(brand_telegrams),
        "website_candidates": _unique_strings(websites),
        "proof_urls": _unique_strings(proof_urls),
        "search_queries_used": search_queries_used,
    }


def resolve_company_routes(company: dict) -> dict:
    company_name = str(company.get("name") or "").strip()
    aliases = _unique_strings([company_name, *list(company.get("aliases") or [])])
    website = _preferred_website(company)
    candidate_names = _extract_person_names_from_company(company)

    people_result = search_decision_makers(company_name, aliases=aliases, use_firecrawl=False)
    candidate_names.extend(person.full_name for person in people_result.decision_makers if person.full_name)
    candidate_names = _unique_strings(candidate_names)

    person_resolutions: list[dict] = []
    person_instagrams: list[str] = []
    person_telegrams: list[str] = []
    person_emails: list[str] = []
    proof_urls: list[str] = []
    search_queries_used: list[str] = []

    for person_name in candidate_names[:4]:
        person_result = _search_person_socials(company_name, person_name)
        search_queries_used.extend(person_result["search_queries_used"])
        proof_urls.extend(person_result["proof_urls"])
        person_instagrams.extend(person_result["instagram_urls"])
        person_telegrams.extend(person_result["telegram_urls"])
        person_emails.extend(person_result["emails"])
        person_resolutions.append(
            {
                "person_name": person_name,
                "instagram_urls": person_result["instagram_urls"],
                "telegram_urls": person_result["telegram_urls"],
                "emails": person_result["emails"],
                "proof_urls": person_result["proof_urls"][:5],
            }
        )

    brand_socials = _search_brand_socials(company_name, aliases)
    search_queries_used.extend(brand_socials["search_queries_used"])
    proof_urls.extend(brand_socials["proof_urls"])

    if not website:
        for candidate in brand_socials["website_candidates"]:
            domain = domain_from_url(candidate)
            if domain and not any(noise in domain for noise in NOISE_DOMAINS):
                website = candidate
                break

    site_result = crawl_corporate_site(website, use_firecrawl=False) if website else None
    site_emails = list(site_result.emails) if site_result else []
    site_telegrams = list(site_result.telegrams) if site_result else []
    site_contact_urls = list(site_result.pages_crawled) if site_result else []

    all_named_emails = _unique_strings([*person_emails, *site_emails])
    status, confidence = _status_for_resolution(
        _unique_strings(person_instagrams),
        _unique_strings([*person_telegrams, *site_telegrams]),
        all_named_emails,
        brand_socials["brand_instagrams"],
        brand_socials["brand_telegrams"],
    )

    resolution_notes = []
    if candidate_names:
        resolution_notes.append(f"searched {len(candidate_names[:4])} candidate names")
    if website:
        resolution_notes.append(f"website checked: {website}")
    if people_result.owner_name:
        resolution_notes.append(f"owner hint: {people_result.owner_name}")
    if site_result and site_result.named_contacts:
        resolution_notes.append(f"site named contacts: {len(site_result.named_contacts)}")

    return {
        "brand": company_name,
        "segment": company.get("segment"),
        "nsx_fit": int(company.get("nsx_fit") or 0),
        "website": website,
        "status": status,
        "route_confidence": confidence,
        "candidate_names": candidate_names[:4],
        "person_resolutions": person_resolutions,
        "resolved_instagrams": _unique_strings([*person_instagrams, *brand_socials["brand_instagrams"]]),
        "resolved_telegrams": _unique_strings([*person_telegrams, *brand_socials["brand_telegrams"], *site_telegrams]),
        "resolved_emails": all_named_emails[:8],
        "resolved_contact_urls": _unique_strings(site_contact_urls + brand_socials["website_candidates"])[:10],
        "site_named_contacts": [
            {
                "full_name": person.full_name,
                "position": person.position,
                "department": person.department,
                "source_url": person.source_url,
            }
            for person in (site_result.named_contacts if site_result else [])[:6]
        ],
        "proof_urls": _unique_strings(proof_urls + site_contact_urls)[:12],
        "search_queries_used": _unique_strings(search_queries_used),
        "resolution_notes": "; ".join(resolution_notes),
    }


def build_theblueprint_route_resolutions(shortlist_payload: dict, *, max_workers: int = 6, unresolved_only: bool = False) -> dict:
    companies = list(shortlist_payload.get("companies") or [])
    if unresolved_only:
        companies = [
            company for company in companies
            if not str(company.get("entry_route") or "").strip()
            or "найти" in str(company.get("entry_route") or "").casefold()
            or "через 2 месяца" in str(company.get("entry_route") or "").casefold()
        ]

    resolutions: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(max_workers, 1)) as executor:
        futures = {executor.submit(resolve_company_routes, company): company for company in companies}
        for future in as_completed(futures):
            try:
                resolutions.append(future.result())
            except Exception as exc:
                company = futures[future]
                resolutions.append(
                    {
                        "brand": company.get("name"),
                        "segment": company.get("segment"),
                        "status": "error",
                        "route_confidence": "low",
                        "resolved_instagrams": [],
                        "resolved_telegrams": [],
                        "resolved_emails": [],
                        "resolved_contact_urls": [],
                        "proof_urls": [],
                        "search_queries_used": [],
                        "resolution_notes": f"resolver failed: {exc}",
                    }
                )

    resolutions.sort(key=lambda item: str(item.get("brand") or "").casefold())
    summary = {
        "companies_scanned": len(companies),
        "resolved_person_route": sum(1 for item in resolutions if item.get("status") == "resolved_person_route"),
        "resolved_brand_route": sum(1 for item in resolutions if item.get("status") == "resolved_brand_route"),
        "partial": sum(1 for item in resolutions if item.get("status") == "partial"),
        "unresolved": sum(1 for item in resolutions if item.get("status") == "unresolved"),
        "error": sum(1 for item in resolutions if item.get("status") == "error"),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_from_shortlist": "inputs/theblueprint_career_hiring.yaml",
        "summary": summary,
        "resolutions": resolutions,
    }


def load_yaml_payload(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_route_resolutions_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# The Blueprint stage-3 route resolutions",
        "# Auto-generated person -> Instagram -> Telegram -> site -> contacts resolution pass.",
        "",
    ]
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100)
    path.write_text("\n".join(header) + body, encoding="utf-8")


def write_route_resolutions_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload.get("summary") or {}
    lines = [
        "# The Blueprint Route Resolver Report",
        "",
        f"- Companies scanned: `{summary.get('companies_scanned', 0)}`",
        f"- Resolved person routes: `{summary.get('resolved_person_route', 0)}`",
        f"- Resolved brand routes: `{summary.get('resolved_brand_route', 0)}`",
        f"- Partial: `{summary.get('partial', 0)}`",
        f"- Unresolved: `{summary.get('unresolved', 0)}`",
        f"- Errors: `{summary.get('error', 0)}`",
        "",
    ]

    for item in payload.get("resolutions") or []:
        lines.extend(
            [
                f"## {item.get('brand')}",
                "",
                f"- Segment: `{item.get('segment', '')}`",
                f"- Status: `{item.get('status', '')}`",
                f"- Confidence: `{item.get('route_confidence', '')}`",
            ]
        )
        if item.get("candidate_names"):
            lines.append(f"- Candidate names: {', '.join(item['candidate_names'])}")
        if item.get("resolved_instagrams"):
            lines.append(f"- Instagram: {', '.join(item['resolved_instagrams'][:4])}")
        if item.get("resolved_telegrams"):
            lines.append(f"- Telegram: {', '.join(item['resolved_telegrams'][:4])}")
        if item.get("resolved_emails"):
            lines.append(f"- Emails: {', '.join(item['resolved_emails'][:6])}")
        if item.get("resolved_contact_urls"):
            lines.append(f"- Contact URLs: {', '.join(item['resolved_contact_urls'][:4])}")
        if item.get("resolution_notes"):
            lines.append(f"- Notes: {item['resolution_notes']}")
        lines.append("")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
