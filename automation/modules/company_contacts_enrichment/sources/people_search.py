"""Step 4: OSINT people search for decision-makers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..models import DECISION_MAKER_POSITIONS_RU, PersonContact
from ..web_research import extract_emails_from_text, smart_fetch, smart_search


@dataclass
class PeopleSearchResult:
    decision_makers: list[PersonContact] = field(default_factory=list)
    search_queries_used: list[str] = field(default_factory=list)
    articles_found: list[dict] = field(default_factory=list)
    owner_name: str = ""
    owner_source: str = ""
    errors: list[str] = field(default_factory=list)


SEARCH_QUERIES = [
    '"{company}" директор по маркетингу',
    '"{company}" руководитель PR',
    '"{company}" пресс-служба контакты',
    '"{company}" head of marketing',
    '"{company}" CMO',
    '"{company}" основатель владелец',
    'site:vc.ru "{company}" маркетинг',
    'site:cossa.ru "{company}"',
    '"{company}" пресс-релиз контакты',
]


def _looks_like_person_name(name: str) -> bool:
    lowered = name.casefold()
    if any(token in lowered for token in ("документ", "посмотреть", "ваканси", "контакт", "новост", "карьер")):
        return False
    parts = name.split()
    return 2 <= len(parts) <= 3 and all(len(part) >= 2 for part in parts)


def _extract_person_from_text(text: str, source_url: str) -> list[PersonContact]:
    contacts: list[PersonContact] = []
    seen_names: set[str] = set()

    for position_keyword in DECISION_MAKER_POSITIONS_RU:
        pattern_by_position = re.compile(
            rf"({re.escape(position_keyword)})\s*[:\-\u2014,]\s*([А-ЯЁA-Z][а-яёa-z]+\s+[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)?)",
            re.IGNORECASE,
        )
        pattern_by_name = re.compile(
            rf"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*[, \-\u2014]\s*({re.escape(position_keyword)})",
            re.IGNORECASE,
        )

        for pattern, name_group, position_group in (
            (pattern_by_position, 2, 1),
            (pattern_by_name, 1, 2),
        ):
            for match in pattern.finditer(text):
                name = match.group(name_group).strip()
                position = match.group(position_group).strip()
                if name in seen_names or len(name) <= 4 or not _looks_like_person_name(name):
                    continue
                seen_names.add(name)
                department = (
                    "PR"
                    if any(token in position.lower() for token in ("pr", "пресс", "коммуникац"))
                    else "Marketing"
                    if any(token in position.lower() for token in ("маркетинг", "marketing", "реклам"))
                    else "Leadership"
                    if any(token in position.lower() for token in ("генеральн", "основател", "владел"))
                    else "Other"
                )
                contacts.append(
                    PersonContact(
                        full_name=name,
                        position=position,
                        department=department,
                        source_url=source_url,
                        confidence=0.5,
                    )
                )
    return contacts


def search_decision_makers(company_name: str, *, aliases: list[str] | None = None, use_firecrawl: bool = True) -> PeopleSearchResult:
    result = PeopleSearchResult()
    seen_names: set[str] = set()
    all_aliases = [company_name] + list(aliases or [])

    for query_template in SEARCH_QUERIES:
        query = query_template.replace("{company}", company_name)
        result.search_queries_used.append(query)
        search_results = smart_search(query, limit=3, use_firecrawl=use_firecrawl)

        for item in search_results:
            url = str(item.get("url") or "")
            title = str(item.get("title") or "")
            snippet = str(item.get("snippet") or "")
            combined_check = f"{title} {snippet}".lower()
            if not any(alias.lower() in combined_check for alias in all_aliases):
                continue

            persons = _extract_person_from_text(f"{title} {snippet}", url)
            if any(domain in url for domain in ("vc.ru", "cossa.ru", "sostav.ru", "adindex.ru")):
                content = smart_fetch(url, use_firecrawl=use_firecrawl)
                if content:
                    persons.extend(_extract_person_from_text(content[:5000], url))
                    author_match = re.search(
                        r"(?:автор|author)\s*[:\-\u2014]?\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)",
                        content[:2000],
                        re.IGNORECASE,
                    )
                    if author_match:
                        result.articles_found.append({"title": title, "url": url, "author": author_match.group(1).strip()})
                    emails = extract_emails_from_text(content)
                    for person in persons:
                        if person.email or not emails:
                            continue
                        for email in emails:
                            if any(alias.lower() in email.lower() for alias in all_aliases):
                                person.email = email
                                break

            for person in persons:
                if person.full_name not in seen_names:
                    seen_names.add(person.full_name)
                    result.decision_makers.append(person)

    owner_query = f'"{company_name}" основатель OR владелец OR учредитель'
    owner_results = smart_search(owner_query, limit=3, use_firecrawl=use_firecrawl)
    owner_alias_part = "|".join(re.escape(alias) for alias in all_aliases if alias)
    if owner_alias_part:
        owner_pattern = re.compile(
            rf"(?:основатель|владелец|учредитель|founder|CEO)\s*(?:компании\s*)?(?:[«\"]?(?:{owner_alias_part})[»\"]?\s*)?[:\-\u2014,]\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
            re.IGNORECASE,
        )
        for item in owner_results:
            combined = f"{item.get('title') or ''} {item.get('snippet') or ''}"
            owner_match = owner_pattern.search(combined)
            if not owner_match or result.owner_name:
                continue
            result.owner_name = owner_match.group(1).strip()
            result.owner_source = str(item.get("url") or "")
            if result.owner_name not in seen_names:
                seen_names.add(result.owner_name)
                result.decision_makers.append(
                    PersonContact(
                        full_name=result.owner_name,
                        position="Основатель / владелец",
                        department="Leadership",
                        source_url=result.owner_source,
                        confidence=0.7,
                    )
                )

    return result
