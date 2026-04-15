"""Reduce The Blueprint archive into an outreach-ready hiring shortlist."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import yaml


TARGET_SEGMENTS = ("B", "C", "D", "E")

DIRECT_ROLE_PATTERNS = (
    r"\bpr\b",
    r"\bпиар\b",
    r"маркетинг",
    r"маркетолог",
    r"маркетингов",
    r"marketing",
    r"smm",
    r"контент",
    r"content",
    r"brand",
    r"бренд",
    r"коммуникац",
    r"communications",
    r"influence",
    r"social",
    r"\bcrm\b",
)

CREATIVE_SIGNAL_PATTERNS = (
    r"арт[\s-]?директор",
    r"art director",
    r"creative director",
    r"креатив",
    r"producer",
    r"продюсер",
    r"content[-\s]?creator",
    r"контент[-\s]?(креатор|продюсер)",
    r"event",
    r"визуал",
)

SENIOR_ROLE_PATTERNS = (
    r"директор",
    r"руководител",
    r"\bhead\b",
    r"\blead\b",
    r"\bchief\b",
    r"ведущ",
    r"senior",
    r"старш",
)

JUNIOR_ROLE_PATTERNS = (
    r"стаж",
    r"\bintern\b",
    r"junior",
    r"младш",
    r"trainee",
)

DESIGN_ROLE_PATTERNS = (
    r"designer",
    r"дизайнер",
    r"ретуш",
    r"ux",
    r"ui",
    r"graphic",
    r"презентац",
    r"product design",
)

EXCLUDE_PATTERNS = (
    r"magazine",
    r"media",
    r"journal",
    r"журнал",
    r"издател",
    r"publishing",
    r"museum",
    r"музей",
    r"gallery",
    r"галере",
    r"театр",
    r"theatre",
    r"theater",
    r"philharm",
    r"филармон",
    r"opera",
    r"оркестр",
    r"ballet",
    r"festival",
    r"фестиваль",
    r"foundation",
    r"фонд",
    r"charity",
    r"благотвор",
    r"school",
    r"школ",
    r"university",
    r"университет",
    r"academy",
    r"академ",
    r"research",
    r"наук",
    r"институт",
    r"library",
    r"библиотек",
    r"agency",
    r"агентств",
    r"radio",
    r"\btv\b",
    r"телеканал",
    r"кинотеатр",
    r"developer",
    r"development",
    r"девелоп",
    r"construction",
    r"строй",
    r"estate",
    r"realty",
    r"property",
    r"недвиж",
    r"clinic",
    r"клиник",
    r"medical",
    r"медицин",
    r"church",
    r"монастыр",
    r"культурн",
    r"дом культуры",
    r"усадьб",
)

SEGMENT_D_PATTERNS = (
    r"coffee",
    r"cafe",
    r"café",
    r"restaurant",
    r"pizza",
    r"burger",
    r"bistro",
    r"bar",
    r"bakery",
    r"roasters",
    r"sushi",
    r"pub",
    r"trattoria",
    r"кофе",
    r"кафе",
    r"ресторан",
    r"бар",
    r"пицц",
    r"булоч",
    r"пекар",
    r"кухн",
    r"кофейн",
)

SEGMENT_E_PATTERNS = (
    r"tech",
    r"fintech",
    r"software",
    r"cloud",
    r"saas",
    r"analytics",
    r"platform",
    r"\bapp\b",
    r"edtech",
    r"yandex",
    r"яндекс",
    r"2gis",
    r"2гис",
    r"avito",
    r"\bvk\b",
    r"headhunter",
    r"\bhh\b",
    r"selectel",
    r"контур",
    r"kontur",
    r"skyeng",
    r"yclients",
    r"t-bank",
    r"т-банк",
    r"тинькофф",
    r"tbank",
    r"amediateka",
    r"kinopoisk",
    r"kion",
)

SEGMENT_C_PATTERNS = (
    r"fashion",
    r"beauty",
    r"skin",
    r"cosmetic",
    r"perfume",
    r"jewel",
    r"ювел",
    r"украш",
    r"stylist",
    r"стилист",
    r"мерч",
    r"lookbook",
    r"showroom",
    r"дизайнер одежды",
    r"одежд",
    r"fashion",
    r"космет",
    r"парф",
    r"уход",
    r"ритейл мод",
)

SEGMENT_B_PATTERNS = (
    r"retail",
    r"e-?commerce",
    r"marketplace",
    r"consumer",
    r"fmcg",
    r"beauty",
    r"fashion",
    r"cosmetic",
    r"jewel",
    r"diamond",
    r"luxury",
    r"premium",
    r"home",
    r"decor",
    r"furniture",
    r"appliance",
    r"electronics",
    r"travel",
    r"hotel",
    r"food",
    r"beverage",
    r"sport",
    r"fitness",
    r"ритейл",
    r"космет",
    r"одежд",
    r"ювел",
    r"декор",
    r"мебел",
    r"электрон",
    r"техник",
    r"путешеств",
    r"отел",
    r"еда",
    r"напит",
    r"спорт",
    r"фитнес",
)

EXACT_NON_TARGET_SLUGS = {
    "alpinapablisher",
    "czsivinzavod",
    "creativesamplestudio",
    "developerskaa-kompania-sense",
    "developerskayakompaniyahutton",
    "domkulturyges2",
    "dotcomms",
    "elle",
    "finansymail",
    "glavstroj",
    "grazia",
    "kommersant",
    "kommersantfm",
    "kreativnyjklasternazavode",
    "kulturnyjczentrsolodovnya",
    "klinikaklazko",
    "marieclaire",
    "maxim",
    "mnenieredakcziimozhetnesovpadat",
    "mmoma",
    "mydecor",
    "naukamail",
    "niuvshe",
    "nochlezhka",
    "ostankino-i-kuskovo",
    "palatynalvatolstogo",
    "pawscomms",
    "peopletalk",
    "pioner",
    "podpisnyeizdeliya",
    "proekt-konservacia",
    "proekt-pomos",
    "pushkinskijyu",
    "ran",
    "rbk",
    "rbkstil",
    "reuimenigvplehanova",
    "sashasulim",
    "shoubezfiltrov",
    "silasveta",
    "sobakaru",
    "theblueprint",
    "tzh",
    "usadbakuskovo",
    "weddywood",
    "wedvibes",
    "womanru",
}

SEGMENT_C_SLUG_HINTS = {
    "12storeez",
    "2mood",
    "addagems",
    "aldocoppola",
    "allweneed",
    "avgvst",
    "befree",
    "belleyou",
    "blcv",
    "brendemka",
    "brendsela",
    "donttouchmyskin",
    "emka",
    "ekonika",
    "finnflare",
    "lamoda",
    "loombyrodina",
    "loverepublic",
    "lime",
    "monochrome",
    "miuzdiamonds",
    "poisondrop",
    "sela",
    "studio29",
    "ushatava",
    "yuliawave",
    "zarina",
    "zolotoeyabloko",
}

SEGMENT_D_SLUG_HINTS = {
    "abccoffeeroasters",
    "bar-rovesnik",
    "coffeemania",
    "dodobrands",
    "prime-ride",
    "vkusnoitochka",
    "rostics",
}

SEGMENT_E_SLUG_HINTS = {
    "2gis",
    "amediateka",
    "avito",
    "kion",
    "kinopoisk",
    "magnitadtech",
    "mts",
    "ozon",
    "sber",
    "t2",
    "tbank",
    "vk",
    "yandex",
}

SEGMENT_B_SLUG_HINTS = {
    "alltime",
    "aviasejls",
    "banimalevicha",
    "blar",
    "bork",
    "boscodiciliegi",
    "botrois",
    "cois",
    "fable",
    "imakebags",
    "jenek",
    "kin",
    "kits",
    "leokid",
    "lindadela",
    "miele",
    "naos",
    "nikasport",
    "nrav",
    "omoikiri",
    "oniverse",
    "parureatelier",
    "pitkina",
    "pritch",
    "r4s",
    "rendezvous",
    "restore",
    "rink",
    "samokat",
    "sanchy",
    "scandalemanire",
    "seneca",
    "simplegroup",
    "sportmaster",
    "tehnopark",
    "theayris",
    "tondeo",
    "vassaco",
    "vesnaskoro",
    "volgadream",
    "wayoflivingwol",
}


DIRECT_ROLE_RE = re.compile("|".join(DIRECT_ROLE_PATTERNS), re.IGNORECASE)
CREATIVE_SIGNAL_RE = re.compile("|".join(CREATIVE_SIGNAL_PATTERNS), re.IGNORECASE)
SENIOR_ROLE_RE = re.compile("|".join(SENIOR_ROLE_PATTERNS), re.IGNORECASE)
JUNIOR_ROLE_RE = re.compile("|".join(JUNIOR_ROLE_PATTERNS), re.IGNORECASE)
DESIGN_ROLE_RE = re.compile("|".join(DESIGN_ROLE_PATTERNS), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS), re.IGNORECASE)
SEGMENT_D_RE = re.compile("|".join(SEGMENT_D_PATTERNS), re.IGNORECASE)
SEGMENT_E_RE = re.compile("|".join(SEGMENT_E_PATTERNS), re.IGNORECASE)
SEGMENT_C_RE = re.compile("|".join(SEGMENT_C_PATTERNS), re.IGNORECASE)
SEGMENT_B_RE = re.compile("|".join(SEGMENT_B_PATTERNS), re.IGNORECASE)


def _normalize_brand_key(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^(бренд|brand)\s+", "", text, flags=re.IGNORECASE)
    text = text.replace("’", "'").replace("`", "'")
    return re.sub(r"[^0-9a-zа-яё]+", " ", text.casefold()).strip()


def _safe_parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip()[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _listify(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    return [value]


def _extract_emails_from_value(value) -> list[str]:
    emails: list[str] = []
    if isinstance(value, str):
        if "@" in value:
            emails.append(value)
        return emails
    if isinstance(value, list):
        for item in value:
            emails.extend(_extract_emails_from_value(item))
        return emails
    if isinstance(value, dict):
        for item in value.values():
            emails.extend(_extract_emails_from_value(item))
    return emails


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _merge_hiring_items(items: list[dict]) -> list[dict]:
    keyed: dict[tuple[str, str], dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        source_url = str(item.get("source_url") or item.get("url") or "").strip()
        key = (role.casefold(), source_url.casefold())
        if key not in keyed:
            keyed[key] = dict(item)
            continue

        current = keyed[key]
        published_at = str(item.get("published_at") or "")
        if published_at and not current.get("published_at"):
            current["published_at"] = published_at
        if item.get("marketing_signal"):
            current["marketing_signal"] = True
        if item.get("signal") and not current.get("signal"):
            current["signal"] = item.get("signal")
        if item.get("hired_person") and not current.get("hired_person"):
            current["hired_person"] = item.get("hired_person")
    return list(keyed.values())


def _choose_better_name(current: str, candidate: str) -> str:
    if not current:
        return candidate
    current_prefixed = current.casefold().startswith(("бренд ", "brand "))
    candidate_prefixed = candidate.casefold().startswith(("бренд ", "brand "))
    if current_prefixed and not candidate_prefixed:
        return candidate
    if candidate_prefixed and not current_prefixed:
        return current
    return candidate if len(candidate) < len(current) else current


def _merge_archive_companies(archive_companies: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}

    for company in archive_companies:
        if not isinstance(company, dict):
            continue
        key = _normalize_brand_key(company.get("name") or "")
        if not key:
            continue

        record = grouped.setdefault(
            key,
            {
                "name": str(company.get("name") or ""),
                "aliases": [],
                "contacts": {"emails": [], "phones": []},
                "hiring": [],
                "marketing_signal": False,
                "blueprint_brand_slugs": [],
                "blueprint_brand_urls": [],
                "blueprint_urls": [],
            },
        )

        record["name"] = _choose_better_name(record["name"], str(company.get("name") or ""))
        record["aliases"].append(str(company.get("name") or ""))
        record["aliases"].extend(_listify(company.get("aliases")))
        record["marketing_signal"] = bool(record["marketing_signal"] or company.get("marketing_signal"))

        contacts = company.get("contacts") or {}
        if isinstance(contacts, dict):
            record["contacts"]["emails"].extend(_listify(contacts.get("emails")))
            record["contacts"]["phones"].extend(_listify(contacts.get("phones")))

        record["hiring"].extend(_listify(company.get("hiring")))
        record["blueprint_brand_slugs"].extend(_listify(company.get("blueprint_brand_slugs")))
        record["blueprint_brand_urls"].extend(_listify(company.get("blueprint_brand_urls")))
        record["blueprint_urls"].extend(_listify(company.get("blueprint_urls")))

    merged: list[dict] = []
    for record in grouped.values():
        record["aliases"] = _unique_strings(record["aliases"])
        record["contacts"]["emails"] = _unique_strings(record["contacts"]["emails"])
        record["contacts"]["phones"] = _unique_strings(record["contacts"]["phones"])
        record["hiring"] = _merge_hiring_items(record["hiring"])
        record["blueprint_brand_slugs"] = _unique_strings(record["blueprint_brand_slugs"])
        record["blueprint_brand_urls"] = _unique_strings(record["blueprint_brand_urls"])
        record["blueprint_urls"] = _unique_strings(record["blueprint_urls"])
        merged.append(record)

    return merged


def _build_manual_override_map(existing_payload: dict) -> dict[str, dict]:
    overrides: dict[str, dict] = {}

    for company in list(existing_payload.get("companies") or []):
        if not isinstance(company, dict):
            continue
        contacts = company.get("contacts") or {}
        has_manual_contacts = isinstance(contacts, dict) and any(key not in {"emails", "phones"} for key in contacts)
        is_manual_candidate = bool(
            str(company.get("entity_type") or "") == "channel"
            or company.get("angle")
            or company.get("entry_route")
            or has_manual_contacts
        )
        if not is_manual_candidate:
            continue
        for raw_key in [company.get("name"), *list(company.get("aliases") or [])]:
            key = _normalize_brand_key(str(raw_key or ""))
            if key:
                overrides[key] = company
    return overrides


def _recent_roles(hiring_items: list[dict], cutoff: datetime) -> list[dict]:
    recent: list[dict] = []
    for item in hiring_items:
        published_at = _safe_parse_date(str(item.get("published_at") or ""))
        if not published_at or published_at < cutoff:
            continue
        enriched = dict(item)
        enriched["_published_at_dt"] = published_at
        recent.append(enriched)
    recent.sort(key=lambda item: item["_published_at_dt"], reverse=True)
    return recent


def _is_direct_role(role: str) -> bool:
    return bool(DIRECT_ROLE_RE.search(str(role or "")))


def _is_creative_signal(role: str) -> bool:
    return bool(CREATIVE_SIGNAL_RE.search(str(role or "")))


def _is_senior_role(role: str) -> bool:
    return bool(SENIOR_ROLE_RE.search(str(role or "")))


def _is_junior_role(role: str) -> bool:
    return bool(JUNIOR_ROLE_RE.search(str(role or "")))


def _is_design_role(role: str) -> bool:
    return bool(DESIGN_ROLE_RE.search(str(role or "")))


def _should_exclude(company: dict) -> bool:
    slug_set = {str(slug or "").casefold() for slug in company.get("blueprint_brand_slugs") or []}
    if slug_set & EXACT_NON_TARGET_SLUGS:
        return True

    haystacks = [str(company.get("name") or "")]
    haystacks.extend(str(slug or "") for slug in slug_set)
    combined = " | ".join(haystacks)
    return bool(EXCLUDE_RE.search(combined))


def _has_segment_b_signal(company: dict) -> bool:
    slug_set = {str(slug or "").casefold() for slug in company.get("blueprint_brand_slugs") or []}
    if slug_set & SEGMENT_B_SLUG_HINTS:
        return True

    name = str(company.get("name") or "")
    slugs = " ".join(str(slug or "") for slug in slug_set)
    combined = f"{name} {slugs}"
    return bool(SEGMENT_B_RE.search(combined))


def _infer_segment(company: dict, override: dict | None) -> str:
    if override:
        segment = str(override.get("segment") or "").strip()
        if segment in TARGET_SEGMENTS:
            return segment

    slugs = " ".join(str(slug or "") for slug in company.get("blueprint_brand_slugs") or [])
    name = str(company.get("name") or "")
    roles_text = " ".join(str(item.get("role") or "") for item in company.get("hiring") or [])
    haystack = f"{name} {slugs} {roles_text}"

    slug_set = {str(slug or "").casefold() for slug in company.get("blueprint_brand_slugs") or []}
    if slug_set & SEGMENT_D_SLUG_HINTS or SEGMENT_D_RE.search(haystack):
        return "D"
    if slug_set & SEGMENT_E_SLUG_HINTS or SEGMENT_E_RE.search(haystack):
        return "E"
    if slug_set & SEGMENT_C_SLUG_HINTS or SEGMENT_C_RE.search(haystack):
        return "C"
    if _has_segment_b_signal(company):
        return "B"
    return ""


def _infer_industry(segment: str, company: dict, override: dict | None) -> str:
    if override and override.get("industry"):
        return str(override.get("industry"))

    name = str(company.get("name") or "").casefold()
    if segment == "D":
        if any(keyword in name for keyword in ("coffee", "коф", "pizza", "пицц")):
            return "horeca / coffee / casual dining"
        return "horeca / restaurant group"
    if segment == "E":
        if any(keyword in name for keyword in ("bank", "банк", "t-bank", "тинькофф")):
            return "fintech / digital services"
        return "tech / SaaS / digital"
    if segment == "C":
        if any(keyword in name for keyword in ("skin", "beauty", "косм", "perfume", "парф")):
            return "beauty / skincare / cosmetics"
        if any(keyword in name for keyword in ("avgvst", "jewel", "ювел", "diamond", "watch")):
            return "jewelry / accessories"
        return "fashion / beauty / lifestyle DTC"
    return "consumer / retail / premium brand"


def _priority_from_fit(nsx_fit: int) -> str:
    if nsx_fit >= 3:
        return "high"
    if nsx_fit == 2:
        return "medium"
    return "low"


def _latest_role_date(items: list[dict]) -> datetime | None:
    latest = None
    for item in items:
        dt = item.get("_published_at_dt")
        if dt and (latest is None or dt > latest):
            latest = dt
    return latest


def _score_company(
    segment: str,
    direct_roles: list[dict],
    creative_roles: list[dict],
    emails: list[str],
    override: dict | None,
    now: datetime,
) -> tuple[int, int, bool]:
    latest = _latest_role_date([*direct_roles, *creative_roles])
    recent_days = (now - latest).days if latest else 9999
    has_senior_direct = any(_is_senior_role(str(item.get("role") or "")) for item in direct_roles)
    non_junior_direct = [item for item in direct_roles if not _is_junior_role(str(item.get("role") or ""))]
    override_fit = int((override or {}).get("nsx_fit") or 0)
    has_override = override_fit >= 2

    if segment == "B":
        keep = bool(has_override or has_senior_direct or len(non_junior_direct) >= 2 or (emails and non_junior_direct))
    else:
        keep = bool(has_override or non_junior_direct or has_senior_direct or (segment in {"C", "D"} and direct_roles))

    if not keep:
        return 0, 1, False

    score = 0
    score += {"C": 18, "D": 18, "B": 12, "E": 14}.get(segment, 0)
    score += 16 * min(len(non_junior_direct), 3)
    score += 8 * min(len(creative_roles), 2)
    if has_senior_direct:
        score += 14
    if emails:
        score += 10
    if has_override:
        score += 12
    if recent_days <= 60:
        score += 14
    elif recent_days <= 120:
        score += 10
    elif recent_days <= 240:
        score += 6

    if override_fit >= 3 or (has_senior_direct and (emails or len(non_junior_direct) >= 2 or segment in {"C", "D"})):
        return score, 3, True
    if segment in {"C", "D", "E"} and (non_junior_direct or has_override):
        return score, 2, True
    if segment == "B" and (has_senior_direct or len(non_junior_direct) >= 2 or emails or has_override):
        return score, 2, True
    return score, 1, True


def _merge_contacts(auto_contacts: dict, override_contacts) -> dict:
    merged = {}
    if isinstance(override_contacts, dict):
        merged.update(override_contacts)
    merged["emails"] = _unique_strings(
        [*_extract_emails_from_value(override_contacts), *list(auto_contacts.get("emails") or [])]
    )
    merged["phones"] = _unique_strings(list(auto_contacts.get("phones") or []))
    return merged


def _hiring_priority(item: dict) -> tuple[int, float, str]:
    role = str(item.get("role") or "")
    published_dt = _safe_parse_date(str(item.get("published_at") or ""))
    published_rank = -published_dt.timestamp() if published_dt else 0.0

    if item.get("signal") or item.get("hired_person"):
        return (0, published_rank, role.casefold())
    if _is_direct_role(role) and not _is_design_role(role) and not _is_junior_role(role):
        return (1, published_rank, role.casefold())
    if _is_direct_role(role) and not _is_design_role(role):
        return (2, published_rank, role.casefold())
    if _is_creative_signal(role) or _is_design_role(role):
        return (3, published_rank, role.casefold())
    return (4, published_rank, role.casefold())


def _merge_hiring_for_output(relevant_hiring: list[dict], override: dict | None, *, max_items: int = 5) -> list[dict]:
    items = []
    if override and override.get("hiring"):
        items.extend(_listify(override.get("hiring")))
    items.extend(relevant_hiring)
    merged = _merge_hiring_items(items)
    merged.sort(key=_hiring_priority)
    trimmed = []
    for item in merged[:max_items]:
        cleaned = {k: v for k, v in item.items() if not str(k).startswith("_")}
        trimmed.append(cleaned)
    return trimmed


def _signal_reason(direct_roles: list[dict], creative_roles: list[dict], window_days: int) -> str:
    direct_titles = [str(item.get("role") or "").strip() for item in direct_roles[:3] if str(item.get("role") or "").strip()]
    creative_titles = [str(item.get("role") or "").strip() for item in creative_roles[:2] if str(item.get("role") or "").strip()]
    parts: list[str] = []
    if direct_titles:
        parts.append(f"Fresh direct roles in last {window_days}d: {', '.join(direct_titles)}.")
    if creative_titles:
        parts.append(f"Creative content signals: {', '.join(creative_titles)}.")
    return " ".join(parts)


def _build_note(segment: str, signal_reason: str) -> str:
    if segment == "C":
        prefix = "DTC brand with current content/brand hiring signal."
    elif segment == "D":
        prefix = "HoReCa brand with current marketing/content hiring signal."
    elif segment == "E":
        prefix = "Tech/digital brand with current marketing/content hiring signal."
    else:
        prefix = "Strong consumer brand with current marketing/content hiring signal."
    return f"{prefix} {signal_reason}".strip()


def build_theblueprint_shortlist_payload(
    archive_payload: dict,
    *,
    existing_payload: dict | None = None,
    freshness_days: int = 365,
) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=freshness_days)
    existing_payload = existing_payload or {}
    manual_overrides = _build_manual_override_map(existing_payload)
    merged_archive_companies = _merge_archive_companies(list(archive_payload.get("companies") or []))

    selected_companies: list[dict] = []
    excluded_counts = {
        "non_target_patterns": 0,
        "no_fresh_relevant_roles": 0,
        "outside_target_segments": 0,
    }

    for company in merged_archive_companies:
        override = manual_overrides.get(_normalize_brand_key(company.get("name") or ""))
        if override and str(override.get("entity_type") or "") == "channel":
            excluded_counts["non_target_patterns"] += 1
            continue
        if _should_exclude(company):
            excluded_counts["non_target_patterns"] += 1
            continue

        segment = _infer_segment(company, override)
        if segment not in TARGET_SEGMENTS:
            excluded_counts["outside_target_segments"] += 1
            continue

        recent = _recent_roles(list(company.get("hiring") or []), cutoff)
        direct_roles = [
            item
            for item in recent
            if _is_direct_role(str(item.get("role") or "")) and not _is_design_role(str(item.get("role") or ""))
        ]
        creative_roles = [item for item in recent if _is_creative_signal(str(item.get("role") or ""))]
        non_junior_direct = [item for item in direct_roles if not _is_junior_role(str(item.get("role") or ""))]

        keep_via_override = bool(override and int(override.get("nsx_fit") or 0) >= 2 and company.get("marketing_signal"))
        if not direct_roles and not keep_via_override:
            excluded_counts["no_fresh_relevant_roles"] += 1
            continue
        if direct_roles and not non_junior_direct and not keep_via_override:
            excluded_counts["no_fresh_relevant_roles"] += 1
            continue

        emails = _unique_strings(list((company.get("contacts") or {}).get("emails") or []))
        score, nsx_fit, keep = _score_company(segment, direct_roles, creative_roles, emails, override, now)
        if not keep or nsx_fit < 2:
            excluded_counts["no_fresh_relevant_roles"] += 1
            continue
        signal_reason = _signal_reason(direct_roles, creative_roles, freshness_days)

        output_company = {
            "name": str((override or {}).get("name") or company.get("name") or ""),
            "aliases": _unique_strings([*list((override or {}).get("aliases") or []), *list(company.get("aliases") or [])]),
            "entity_type": "prospect",
            "segment": segment,
            "sector": str((override or {}).get("sector") or _infer_industry(segment, company, override)),
            "priority": str((override or {}).get("priority") or _priority_from_fit(nsx_fit)),
            "industry": _infer_industry(segment, company, override),
            "source": "theblueprint_career_brand_archive",
            "blueprint_brand_slugs": _unique_strings(list(company.get("blueprint_brand_slugs") or [])),
            "blueprint_brand_urls": _unique_strings(list(company.get("blueprint_brand_urls") or [])),
            "blueprint_urls": _unique_strings(list(company.get("blueprint_urls") or [])),
            "contacts": _merge_contacts(company.get("contacts") or {}, (override or {}).get("contacts")),
            "hiring": _merge_hiring_for_output([*direct_roles, *creative_roles], override),
            "marketing_signal": bool(company.get("marketing_signal") or direct_roles),
            "signal_reason": signal_reason,
            "nsx_fit": max(nsx_fit, int((override or {}).get("nsx_fit") or 0)),
            "note": str((override or {}).get("note") or _build_note(segment, signal_reason)),
        }

        if override and override.get("angle"):
            output_company["angle"] = override.get("angle")
        if override and override.get("entry_route"):
            output_company["entry_route"] = override.get("entry_route")

        output_company["_score"] = score
        latest_date = _latest_role_date([*direct_roles, *creative_roles])
        output_company["_latest_role_date"] = latest_date.isoformat() if latest_date else ""
        selected_companies.append(output_company)

    selected_companies.sort(
        key=lambda item: (
            -int(item.get("nsx_fit") or 0),
            -int(item.get("_score") or 0),
            str(item.get("_latest_role_date") or ""),
            str(item.get("name") or "").casefold(),
        ),
        reverse=True,
    )

    segment_counts: dict[str, int] = {}
    for company in selected_companies:
        segment = str(company.get("segment") or "")
        segment_counts[segment] = segment_counts.get(segment, 0) + 1

    shortlist_top20 = [company["name"] for company in selected_companies[:20]]

    cleaned_companies = []
    for company in selected_companies:
        cleaned = {k: v for k, v in company.items() if not str(k).startswith("_")}
        cleaned_companies.append(cleaned)

    return {
        "generated_at": now.isoformat(),
        "generated_from": "output/company_contacts_enrichment/theblueprint_career_brand_archive.yaml",
        "selection_rules": {
            "include_segments": list(TARGET_SEGMENTS),
            "freshness_window_days": freshness_days,
            "exclude_media_culture_non_target": True,
            "require_fresh_marketing_pr_content_roles": True,
        },
        "summary": {
            "archive_company_count": len(list(archive_payload.get("companies") or [])),
            "selected_company_count": len(cleaned_companies),
            "segment_counts": segment_counts,
            "excluded_counts": excluded_counts,
        },
        "shortlist_top20": shortlist_top20,
        "companies": cleaned_companies,
    }


def load_yaml_payload(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_theblueprint_shortlist(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# The Blueprint career hiring shortlist",
        "# Auto-generated from full brand archive output.",
        "# This file keeps only target segments B/C/D/E with fresh marketing/PR/content hiring signals.",
        "",
    ]
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120)
    path.write_text("\n".join(header) + body, encoding="utf-8")
