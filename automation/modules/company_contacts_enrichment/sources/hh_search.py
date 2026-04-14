"""Step 3: HH.ru company intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..models import PersonContact
from ..web_research import extract_emails_from_text, extract_phones_from_text, smart_fetch, smart_search


@dataclass
class HHResult:
    employer_url: str = ""
    employer_name: str = ""
    employer_description: str = ""
    company_size: str = ""
    industry: str = ""
    relevant_vacancies: list[dict] = field(default_factory=list)
    marketing_dept_exists: bool = False
    pr_dept_exists: bool = False
    video_content_need: bool = False
    hr_contacts: list[PersonContact] = field(default_factory=list)
    total_active_vacancies: int = 0
    marketing_vacancies_count: int = 0
    raw_text: str = ""
    errors: list[str] = field(default_factory=list)


MARKETING_VACANCY_KEYWORDS = (
    "маркетинг",
    "маркетолог",
    "marketing",
    "бренд-менеджер",
    "brand manager",
    "digital",
    "smm",
    "контент",
    "content",
    "реклама",
    "медиа",
    "media",
    "pr",
    "пресс",
    "коммуникац",
    "видео",
    "video",
    "продакшн",
    "production",
    "креатив",
    "creative",
    "дизайн",
    "design",
)


def search_hh_company(company_name: str, *, aliases: list[str] | None = None, use_firecrawl: bool = True) -> HHResult:
    result = HHResult()
    search_names = [company_name] + list(aliases or [])
    employer_url = ""

    for search_name in search_names:
        query = f'site:hh.ru "{search_name}" вакансии'
        search_results = smart_search(query, limit=5, use_firecrawl=use_firecrawl)
        for item in search_results:
            url = str(item.get("url") or "")
            if "hh.ru/employer/" in url:
                employer_url = url
                break
        if employer_url:
            break

    if employer_url:
        result.employer_url = employer_url
        content = smart_fetch(employer_url, use_firecrawl=use_firecrawl)
        if content:
            result.raw_text = content[:3000]
            result.employer_name = company_name
            size_match = re.search(r"(\d[\d\s]*\d)\s*(?:сотрудник|человек|employee)", content, re.IGNORECASE)
            if size_match:
                result.company_size = size_match.group(1).strip()

    marketing_queries = [
        f'site:hh.ru "{company_name}" маркетинг OR PR OR видео OR контент',
        f'site:hh.ru "{company_name}" marketing OR brand OR digital',
    ]

    seen_vacancy_urls: set[str] = set()
    for marketing_query in marketing_queries:
        marketing_results = smart_search(marketing_query, limit=5, use_firecrawl=use_firecrawl)
        for item in marketing_results:
            url = str(item.get("url") or "")
            title = str(item.get("title") or "")
            snippet = str(item.get("snippet") or "")
            combined = f"{title} {snippet}".lower()

            if "hh.ru/vacancy/" not in url or url in seen_vacancy_urls:
                continue
            if not any(keyword in combined for keyword in MARKETING_VACANCY_KEYWORDS):
                continue

            seen_vacancy_urls.add(url)
            vacancy_info: dict = {"title": title, "url": url, "snippet": snippet}
            vacancy_content = smart_fetch(url, use_firecrawl=use_firecrawl)
            if vacancy_content:
                emails = extract_emails_from_text(vacancy_content)
                phones = extract_phones_from_text(vacancy_content)
                name_match = re.search(
                    r"(?:контактное лицо|contact person|рекрутер|HR)\s*[:\-\u2014]?\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
                    vacancy_content,
                    re.IGNORECASE,
                )
                if name_match:
                    vacancy_info["hr_name"] = name_match.group(1).strip()
                    result.hr_contacts.append(
                        PersonContact(
                            full_name=name_match.group(1).strip(),
                            position="HR / рекрутер",
                            department="HR",
                            email=emails[0] if emails else "",
                            phone=phones[0] if phones else "",
                            source_url=url,
                            confidence=0.5,
                        )
                    )
                if emails:
                    vacancy_info["hr_email"] = emails[0]
                if phones:
                    vacancy_info["hr_phone"] = phones[0]

            result.relevant_vacancies.append(vacancy_info)
            if any(keyword in combined for keyword in ("маркетинг", "маркетолог", "marketing", "brand")):
                result.marketing_dept_exists = True
            if any(keyword in combined for keyword in ("pr", "пресс", "коммуникац", "press")):
                result.pr_dept_exists = True
            if any(keyword in combined for keyword in ("видео", "video", "продакшн", "production")):
                result.video_content_need = True

    result.marketing_vacancies_count = len(result.relevant_vacancies)
    return result
