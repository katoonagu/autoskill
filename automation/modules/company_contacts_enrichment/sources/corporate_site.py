"""Step 2: Corporate website deep crawl."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field

from ..models import CONTACT_PAGE_PATHS, DECISION_MAKER_POSITIONS_RU, PersonContact
from ..web_research import (
    domain_from_url,
    extract_emails_from_text,
    extract_phones_from_text,
    extract_telegrams_from_text,
    fetch_urllib_html,
    smart_fetch,
)


@dataclass
class CorporateSiteResult:
    website: str = ""
    pages_crawled: list[str] = field(default_factory=list)
    pages_failed: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    telegrams: list[str] = field(default_factory=list)
    contact_form_urls: list[str] = field(default_factory=list)
    named_contacts: list[PersonContact] = field(default_factory=list)
    raw_texts: dict[str, str] = field(default_factory=dict)


def _build_contact_urls(base_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(base_url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or domain_from_url(base_url)
    if not netloc:
        return []

    base = f"{scheme}://{netloc}"
    urls: list[str] = [base]
    seen = {base.rstrip("/")}

    for path in CONTACT_PAGE_PATHS:
        candidate = f"{base}{path}"
        normalized = candidate.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            urls.append(candidate)
    return urls


def _classify_position(position: str) -> str:
    lowered = position.lower()
    if any(token in lowered for token in ("pr", "пресс", "коммуникац", "сми")):
        return "PR"
    if any(token in lowered for token in ("маркетинг", "marketing", "реклам", "бренд", "brand")):
        return "Marketing"
    if any(token in lowered for token in ("генеральн", "основател", "владел", "учред", "ceo", "director")):
        return "Leadership"
    return "Other"


def _looks_like_person_name(name: str) -> bool:
    lowered = name.casefold()
    if any(token in lowered for token in ("документ", "посмотреть", "ваканси", "контакт", "новост", "карьер")):
        return False
    parts = name.split()
    return 2 <= len(parts) <= 3 and all(len(part) >= 2 for part in parts)


def _extract_named_contacts_from_text(text: str) -> list[PersonContact]:
    contacts: list[PersonContact] = []
    seen_names: set[str] = set()

    for position_keyword in DECISION_MAKER_POSITIONS_RU:
        pattern_by_position = re.compile(
            rf"({re.escape(position_keyword)})\s*[:\-\u2014\u2013]?\s*([А-ЯЁA-Z][а-яёa-z]+\s+[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)?)",
            re.IGNORECASE,
        )
        pattern_by_name = re.compile(
            rf"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*[, \-\u2014\u2013]\s*({re.escape(position_keyword)})",
            re.IGNORECASE,
        )

        for pattern, name_group, position_group in (
            (pattern_by_position, 2, 1),
            (pattern_by_name, 1, 2),
        ):
            for match in pattern.finditer(text):
                name = match.group(name_group).strip()
                position = match.group(position_group).strip()
                if name in seen_names or not _looks_like_person_name(name):
                    continue
                seen_names.add(name)
                contacts.append(
                    PersonContact(
                        full_name=name,
                        position=position,
                        department=_classify_position(position_keyword),
                        confidence=0.6,
                    )
                )

    return contacts


def _detect_contact_forms(html: str, base_url: str) -> list[str]:
    forms: list[str] = []
    form_actions = re.findall(r'<form[^>]+action=["\']([^"\']+)["\']', html or "", re.IGNORECASE)
    for action in form_actions:
        if not any(keyword in action.lower() for keyword in ("contact", "feedback", "form", "obratna")):
            continue
        if action.startswith("http"):
            forms.append(action)
        elif action.startswith("/"):
            parsed = urllib.parse.urlparse(base_url)
            forms.append(f"{parsed.scheme}://{parsed.netloc}{action}")
    return forms


def crawl_corporate_site(website: str, *, use_firecrawl: bool = True) -> CorporateSiteResult:
    result = CorporateSiteResult(website=website)
    all_emails: list[str] = []
    all_phones: list[str] = []
    all_telegrams: list[str] = []
    all_named: list[PersonContact] = []

    for url in _build_contact_urls(website)[:15]:
        content = smart_fetch(url, use_firecrawl=use_firecrawl)
        if not content:
            result.pages_failed.append(url)
            continue

        result.pages_crawled.append(url)
        result.raw_texts[url] = content[:2000]
        all_emails.extend(extract_emails_from_text(content))
        all_phones.extend(extract_phones_from_text(content))
        all_telegrams.extend(extract_telegrams_from_text(content))

        named = _extract_named_contacts_from_text(content)
        for person in named:
            person.source_url = url
        all_named.extend(named)

        html = fetch_urllib_html(url)
        if html:
            result.contact_form_urls.extend(_detect_contact_forms(html, url))

    result.emails = list(dict.fromkeys(all_emails))
    result.phones = list(dict.fromkeys(all_phones))
    result.telegrams = list(dict.fromkeys(all_telegrams))
    result.contact_form_urls = list(dict.fromkeys(result.contact_form_urls))

    seen_names: set[str] = set()
    for person in all_named:
        if person.full_name not in seen_names:
            seen_names.add(person.full_name)
            result.named_contacts.append(person)

    return result
