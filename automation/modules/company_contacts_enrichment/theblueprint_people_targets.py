"""Build outreach-ready people targets from The Blueprint shortlist."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SEGMENT_WEIGHTS = {
    "C": 35,
    "D": 33,
    "B": 26,
    "E": 20,
}

PRIORITY_WEIGHTS = {
    "high": 8,
    "medium": 4,
    "low": 0,
}

ROLE_SIGNAL_KEYWORDS = (
    "marketing",
    "маркет",
    "brand",
    "бренд",
    "pr",
    "коммуникац",
    "content",
    "контент",
    "smm",
    "influence",
    "crm",
    "digital",
    "producer",
    "продюс",
    "event",
)

SENIOR_ROLE_KEYWORDS = (
    "director",
    "директор",
    "head",
    "lead",
    "manager",
    "менедж",
    "руковод",
    "founder",
    "co-owner",
    "owner",
    "ceo",
)

GENERIC_EMAIL_PREFIXES = (
    "info",
    "hello",
    "hr",
    "job",
    "jobs",
    "career",
    "cv",
    "pr",
    "press",
    "marketing",
    "support",
    "admin",
)

PUBLIC_INTEL: dict[str, dict[str, Any]] = {
    "befree": {
        "priority_bonus": 16,
        "why_now": "Новый marketing manager Евгений Лагутин. Это лучший триггер на тест нового продакшна в первые 30-60 дней.",
        "write_first_to": {
            "name": "Евгений Лагутин",
            "role": "Marketing Manager",
            "route": "person-first via industry mentions, then brand Telegram fallback",
        },
        "person_candidates": [
            {
                "name": "Евгений Лагутин",
                "role": "Marketing Manager",
                "route_priority": "primary",
                "email": "",
                "instagram_url": "",
                "telegram_url": "",
                "confidence": "medium",
                "note": "Имя зафиксировано по hiring signal, но публичный персональный social-route еще не закрыт.",
                "proof_urls": [
                    "https://theblueprint.ru/career/brand/befree",
                    "https://theblueprint.ru/career/39242",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official brand Telegram",
                "url": "https://t.me/befree_community",
                "confidence": "high",
            },
            {
                "platform": "website",
                "label": "Brand site",
                "url": "https://befree.ru/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/befree",
            "https://t.me/befree_community",
        ],
        "next_gap": "Нужно добить персональный Instagram/Telegram Евгения Лагутина через vc.ru, Cossa, AdIndex и выступления.",
        "next_search_queries": [
            "\"Евгений Лагутин\" Befree",
            "\"Евгений Лагутин\" Instagram",
            "\"Евгений Лагутин\" Telegram",
            "site:vc.ru \"Евгений Лагутин\"",
        ],
    },
    "emka": {
        "priority_bonus": 14,
        "why_now": "Прохор Шаляпин только что стал PR-менеджером бренда. Новый PR-руководитель почти всегда ищет быстрые заметные кейсы.",
        "write_first_to": {
            "name": "Прохор Шаляпин",
            "role": "PR-менеджер",
            "route": "person-first via Instagram or Telegram",
        },
        "person_candidates": [
            {
                "name": "Прохор Шаляпин",
                "role": "PR-менеджер",
                "route_priority": "primary",
                "email": "",
                "instagram_url": "https://www.instagram.com/shalyapin_official/",
                "telegram_url": "https://t.me/aChaliapin",
                "confidence": "high",
                "note": "Публичная персона, поэтому warm-cold через личный DM имеет смысл.",
                "proof_urls": [
                    "https://theblueprint.ru/career/brand/emka",
                    "https://www.instagram.com/reel/DWlRI6AiMRG/",
                    "https://t.me/s/aChaliapin",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "website",
                "label": "Brand site",
                "url": "https://emka-fashion.ru/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/emka",
            "https://www.instagram.com/reel/DWlRI6AiMRG/",
            "https://t.me/s/aChaliapin",
        ],
        "next_gap": "Если личный DM не зайдет, дожать через брендовый PR-mailbox и подтверждение нового PR owner в профильных медиа.",
        "next_search_queries": [
            "\"Прохор Шаляпин\" Emka",
            "\"Прохор Шаляпин\" Instagram",
            "\"Прохор Шаляпин\" Telegram",
        ],
    },
    "ushatava": {
        "priority_bonus": 16,
        "why_now": "Ushatava открывает или усиливает обувную и аксессуарную категорию. Это прямой launch-content кейс под кампанию и product reels.",
        "write_first_to": {
            "name": "Нино Шаматавa",
            "role": "Creative / Content Director, co-founder",
            "route": "person-first via Instagram, then official photo/content contact",
        },
        "person_candidates": [
            {
                "name": "Нино Шаматава",
                "role": "Content director / co-founder",
                "route_priority": "primary",
                "email": "photo@ushatava.com",
                "instagram_url": "https://www.instagram.com/ninoshenka/",
                "telegram_url": "",
                "confidence": "high",
                "note": "Официальный contacts page привязывает Nino Shamatava к content/photo contact.",
                "proof_urls": [
                    "https://en.ushatava.ru/about/contacts/",
                    "https://www.instagram.com/ninoshenka/",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official client service bot",
                "url": "https://t.me/Ushatava_clientsbot",
                "confidence": "high",
            },
            {
                "platform": "website",
                "label": "Official contacts",
                "url": "https://en.ushatava.ru/about/contacts/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/ushatava",
            "https://www.hr.ushatava.ru/developing_shoes",
            "https://en.ushatava.ru/about/contacts/",
        ],
        "next_gap": "Отдельно найти личный route Алисы Ушатовой, чтобы писать двум лицам с разным углом: launch и brand.",
        "next_search_queries": [
            "\"Алиса Ушатова\" Instagram",
            "\"Алиса Ушатова\" Telegram",
            "\"Нино Шаматава\" Telegram",
        ],
    },
    "lamoda": {
        "priority_bonus": 10,
        "why_now": "Одновременно видны digital marketing, STM design, event и producer signals. Это значит, что Lamoda строит контент-поток, а не единичную кампанию.",
        "write_first_to": {
            "name": "Brand / STM owner (name to confirm)",
            "role": "Private label / digital marketing",
            "route": "role-first via named Lamoda email plus brand Telegram",
        },
        "person_candidates": [
            {
                "name": "Darya Sokolova",
                "role": "Lamoda contact from Blueprint hiring trail",
                "route_priority": "primary",
                "email": "darya.sokolova@lamoda.ru",
                "instagram_url": "",
                "telegram_url": "",
                "confidence": "medium",
                "note": "Рабочая точка входа для запроса контакта бренд- или private-label owner.",
                "proof_urls": [
                    "https://theblueprint.ru/career/brand/lamoda",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official brand Telegram",
                "url": "https://t.me/lamoda_na_svyazi",
                "confidence": "high",
            },
            {
                "platform": "instagram",
                "label": "Official brand Instagram",
                "url": "https://www.instagram.com/lamoda/",
                "confidence": "high",
            },
            {
                "platform": "website",
                "label": "Career site",
                "url": "https://job.lamoda.ru/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/lamoda",
            "https://t.me/lamoda_na_svyazi",
            "https://job.lamoda.ru/",
        ],
        "next_gap": "Нужно имя владельца STM/private label или текущего brand lead, иначе писать придется через bridge contact.",
        "next_search_queries": [
            "\"Lamoda\" \"private label\" маркетинг",
            "\"Lamoda\" brand director",
            "\"Lamoda\" Telegram",
        ],
    },
    "don't touch my skin": {
        "priority_bonus": 14,
        "why_now": "Идет найм руководителя отдела маркетинга. Это момент, когда founder и новый маркетинг-руководитель будут собирать новый стек подрядчиков.",
        "write_first_to": {
            "name": "Адэль Мифтахова",
            "role": "Founder",
            "route": "person-first via Telegram, then brand Instagram and direct founder-related email trail",
        },
        "person_candidates": [
            {
                "name": "Адэль Мифтахова",
                "role": "Founder",
                "route_priority": "primary",
                "email": "",
                "instagram_url": "https://www.instagram.com/adeliamft/",
                "telegram_url": "https://t.me/donttouchmyface",
                "confidence": "high",
                "note": "Telegram bio прямо привязывает Адэль к DTMS; Instagram handle подтверждается публичными упоминаниями.",
                "proof_urls": [
                    "https://t.me/donttouchmyface",
                    "https://www.instagram.com/p/B4KAFY8otyw/",
                    "https://telegram.me/s/donttouchmyface?before=2227",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "instagram",
                "label": "Official brand Instagram",
                "url": "https://www.instagram.com/dtmskin/",
                "confidence": "high",
            },
            {
                "platform": "website",
                "label": "Brand site",
                "url": "https://dtmskin.com/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/donttouchmyskin",
            "https://t.me/donttouchmyface",
            "https://www.instagram.com/dtmskin/",
        ],
        "next_gap": "Через 2-4 недели обновить имя нового head of marketing и писать парой: founder + marketer.",
        "next_search_queries": [
            "\"Don't Touch My Skin\" \"руководитель отдела маркетинга\"",
            "\"Адэль Мифтахова\" Instagram",
            "\"Адэль Мифтахова\" Telegram",
        ],
    },
    "finn flare": {
        "priority_bonus": 10,
        "why_now": "Ищут SMM-менеджера. Это обычно значит, что дистрибуцию строят in-house, а тяжелый видео-продакшн готовы отдавать наружу.",
        "write_first_to": {
            "name": "Named HR bridge + marketing/pr mailbox",
            "role": "Bridge to marketing owner",
            "route": "named-email-first with parallel official Telegram/Instagram touch",
        },
        "person_candidates": [
            {
                "name": "Unknown marketing owner",
                "role": "SMM / marketing",
                "route_priority": "primary",
                "email": "chernovitskaya@finn-flare.ru",
                "instagram_url": "",
                "telegram_url": "",
                "confidence": "medium",
                "note": "Надежный bridge-contact из вакансии; дальше задача получить owner в маркетинге.",
                "proof_urls": [
                    "https://theblueprint.ru/career/brand/finnflare",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official brand Telegram",
                "url": "https://t.me/finnflareofficial",
                "confidence": "high",
            },
            {
                "platform": "instagram",
                "label": "Official brand Instagram",
                "url": "https://www.instagram.com/finn_flare_official/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/finnflare",
            "https://t.me/finnflareofficial",
        ],
        "next_gap": "Нужно имя текущего маркетинг/бренд owner, чтобы уйти от HR-bridge к buyer.",
        "next_search_queries": [
            "\"Finn Flare\" marketing director",
            "\"Finn Flare\" brand director",
            "\"Finn Flare\" Telegram",
        ],
    },
    "бар «ровесник»": {
        "priority_bonus": 12,
        "why_now": "Две свежие SMM-роли с фокусом на content и sales. Для HoReCa это почти прямой маркер постоянной потребности в роликах и social formats.",
        "write_first_to": {
            "name": "Александр Мартынов",
            "role": "Co-founder",
            "route": "founder-aware via official Instagram/Telegram and HR Telegram handle",
        },
        "person_candidates": [
            {
                "name": "Александр Мартынов",
                "role": "Co-founder",
                "route_priority": "primary",
                "email": "",
                "instagram_url": "",
                "telegram_url": "",
                "confidence": "medium",
                "note": "Публично подтвержден как сооснователь; прямой social handle еще не закрыт.",
                "proof_urls": [
                    "https://moskvichmag.ru/gorod/v-malom-gnedzdnikovskom-otkroetsya-bar-rovesnik-pryamo-u-ministerstva-kultury/",
                ],
            },
            {
                "name": "HR / studio contact",
                "role": "Hiring bridge",
                "route_priority": "secondary",
                "email": "",
                "instagram_url": "",
                "telegram_url": "https://t.me/HRp2pstudio",
                "confidence": "high",
                "note": "Вакансия напрямую ведет в Telegram handle @HRp2pstudio.",
                "proof_urls": [
                    "https://theblueprint.ru/career/38754",
                    "https://theblueprint.ru/career/brand/bar-rovesnik",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official bar Telegram",
                "url": "https://t.me/rovesnikbar",
                "confidence": "high",
            },
            {
                "platform": "instagram",
                "label": "Official bar Instagram",
                "url": "https://www.instagram.com/rovesnik.bar/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/bar-rovesnik",
            "https://t.me/rovesnikbar",
            "https://www.instagram.com/rovesnik.bar/",
            "https://moskvichmag.ru/gorod/v-malom-gnedzdnikovskom-otkroetsya-bar-rovesnik-pryamo-u-ministerstva-kultury/",
        ],
        "next_gap": "Нужно добить личный Instagram/Telegram Александра Мартынова и второго co-founder для прямого owner outreach.",
        "next_search_queries": [
            "\"Александр Мартынов\" \"Ровесник\" Instagram",
            "\"Александр Мартынов\" \"Ровесник\" Telegram",
            "\"Кирилл\" \"Ровесник\" бар",
        ],
    },
    "bork": {
        "priority_bonus": 10,
        "why_now": "У Bork одновременно видны CRM, brand, SMM и event roles. Это не единичный найм, а работающий контент- и brand-маховик.",
        "write_first_to": {
            "name": "Brand / marketing owner via named Bork email",
            "role": "Brand or CRM marketing",
            "route": "named-email-first, then premium brand socials",
        },
        "person_candidates": [
            {
                "name": "Valeriya Chernova",
                "role": "HR / hiring bridge",
                "route_priority": "primary",
                "email": "valeriya.chernova@bork.com",
                "instagram_url": "",
                "telegram_url": "",
                "confidence": "high",
                "note": "Повторяется в Blueprint-вакансиях как рабочая точка входа.",
                "proof_urls": [
                    "https://theblueprint.ru/career/brand/bork",
                    "https://theblueprint.ru/career/38080",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Official brand Telegram",
                "url": "https://t.me/bork_public",
                "confidence": "high",
            },
            {
                "platform": "instagram",
                "label": "Official brand Instagram",
                "url": "https://www.instagram.com/bork_com/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/bork",
            "https://www.instagram.com/bork_com/",
            "https://t.me/s/bork_public",
        ],
        "next_gap": "Нужно конкретное имя бренд-менеджера или PR owner, чтобы перестать писать через hiring bridge.",
        "next_search_queries": [
            "\"Bork\" \"бренд-менеджер\"",
            "\"Bork\" PR director",
            "\"Valeriya Chernova\" Bork",
        ],
    },
    "yuliawave": {
        "priority_bonus": 11,
        "why_now": "Свежий PR-director signal плюс у founder-led fashion house уже есть прямой personal route, что сильно сокращает путь до решения.",
        "write_first_to": {
            "name": "Юлия Василевская",
            "role": "Founder",
            "route": "person-first via founder Instagram, then CEO / PR email fallback",
        },
        "person_candidates": [
            {
                "name": "Юлия Василевская",
                "role": "Founder",
                "route_priority": "primary",
                "email": "ceo@yuliawave.com",
                "instagram_url": "https://www.instagram.com/yuliawave/",
                "telegram_url": "https://t.me/YULIAWAVE_BRAND",
                "confidence": "high",
                "note": "Founder Instagram прямо указывает на YULIAWAVE; брендовый Telegram доступен как direct contact.",
                "proof_urls": [
                    "https://www.instagram.com/yuliawave/",
                    "https://t.me/YULIAWAVE_BRAND",
                    "https://theblueprint.ru/career/brand/yuliawave",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "instagram",
                "label": "Brand Instagram",
                "url": "https://www.instagram.com/yuliawave.brand/",
                "confidence": "high",
            },
            {
                "platform": "website",
                "label": "Brand contacts",
                "url": "https://yuliawave.com/contact/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/yuliawave",
            "https://www.instagram.com/yuliawave/",
            "https://yuliawave.com/contact/",
        ],
        "next_gap": "Хорошо бы найти имя нового PR director, чтобы писать founder + PR pair.",
        "next_search_queries": [
            "\"YuliaWave\" \"PR-директор\"",
            "\"Юлия Василевская\" Telegram",
        ],
    },
    "2mood": {
        "priority_bonus": 10,
        "why_now": "Свежий найм в SMM и Influence & PR marketing. Это ровно тот момент, когда бренд расширяет контент-команду, но еще не закрыл все production-потребности.",
        "write_first_to": {
            "name": "Полина Подплетенная",
            "role": "Co-owner",
            "route": "person-first via founder Instagram, then brand mailboxes",
        },
        "person_candidates": [
            {
                "name": "Полина Подплетенная",
                "role": "Co-owner",
                "route_priority": "primary",
                "email": "pollyheywork@gmail.com",
                "instagram_url": "https://www.instagram.com/pollyhey/",
                "telegram_url": "",
                "confidence": "high",
                "note": "Instagram bio публично указывает co-owner 2moodstore.",
                "proof_urls": [
                    "https://www.instagram.com/pollyhey/?hl=en",
                    "https://theblueprint.ru/career/brand/2mood",
                ],
            },
            {
                "name": "Кристина Хоронжук",
                "role": "Co-owner",
                "route_priority": "secondary",
                "email": "khkristinaur@gmail.com",
                "instagram_url": "https://www.instagram.com/khkris/",
                "telegram_url": "",
                "confidence": "high",
                "note": "Instagram bio публично указывает co-owner @2moodstore.",
                "proof_urls": [
                    "https://www.instagram.com/khkris/",
                    "https://theblueprint.ru/career/brand/2mood",
                ],
            },
        ],
        "public_routes": [
            {
                "platform": "telegram",
                "label": "Brand Telegram",
                "url": "https://t.me/twomoodstore",
                "confidence": "medium",
            },
            {
                "platform": "instagram",
                "label": "Brand Instagram",
                "url": "https://www.instagram.com/2moodstore/",
                "confidence": "high",
            },
        ],
        "proof_urls": [
            "https://theblueprint.ru/career/brand/2mood",
            "https://www.instagram.com/pollyhey/?hl=en",
            "https://www.instagram.com/khkris/",
            "https://t.me/s/twomoodstore?before=1039",
        ],
        "next_gap": "Нужно имя текущего Influence & PR marketing lead, чтобы писать founders + team owner.",
        "next_search_queries": [
            "\"2MOOD\" \"Influence & PR\"",
            "\"Полина Подплетенная\" Telegram",
            "\"Кристина Хоронжук\" Telegram",
        ],
    },
}


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


def _is_named_email(email: str) -> bool:
    local = email.split("@", 1)[0].casefold()
    return not local.startswith(GENERIC_EMAIL_PREFIXES)


def _role_text(company: dict) -> str:
    chunks = [
        str(company.get("note") or ""),
        str(company.get("angle") or ""),
        str(company.get("entry_route") or ""),
        str(company.get("signal_reason") or ""),
    ]
    for item in _listify(company.get("hiring")):
        if not isinstance(item, dict):
            continue
        chunks.append(str(item.get("role") or ""))
        chunks.append(str(item.get("signal") or ""))
        chunks.append(str(item.get("hired_person") or ""))
    return " ".join(chunks).casefold()


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _route_quality(intel: dict | None, emails: list[str], entry_route: str) -> int:
    score = 0
    if intel and intel.get("person_candidates"):
        person_routes = []
        for person in _listify(intel.get("person_candidates")):
            if isinstance(person, dict):
                person_routes.extend(
                    [
                        str(person.get("instagram_url") or "").strip(),
                        str(person.get("telegram_url") or "").strip(),
                    ]
                )
        score += 20 if any(person_routes) else 8
    if intel and intel.get("public_routes"):
        score += 6
    if entry_route:
        score += 8
    if any(_is_named_email(email) for email in emails):
        score += 4
    if emails:
        score += min(len(emails), 3)
    return score


def _target_score(company: dict, intel: dict | None) -> int:
    segment = str(company.get("segment") or "")
    priority = str(company.get("priority") or "")
    nsx_fit = int(company.get("nsx_fit") or 0)
    emails = _unique_strings(list((company.get("contacts") or {}).get("emails") or []))
    text = _role_text(company)
    score = 0
    score += SEGMENT_WEIGHTS.get(segment, 0)
    score += nsx_fit * 12
    score += PRIORITY_WEIGHTS.get(priority, 0)
    score += 10 if company.get("angle") else 0
    score += 12 if company.get("entry_route") else 0
    score += min(_keyword_hits(text, ROLE_SIGNAL_KEYWORDS), 4) * 3
    score += min(_keyword_hits(text, SENIOR_ROLE_KEYWORDS), 4) * 2
    score += 12 if any(item.get("signal") or item.get("hired_person") for item in _listify(company.get("hiring")) if isinstance(item, dict)) else 0
    score += _route_quality(intel, emails, str(company.get("entry_route") or ""))
    if segment in {"B", "E"} and not any(item.get("hired_person") for item in _listify(company.get("hiring")) if isinstance(item, dict)):
        score -= 6
    if intel:
        score += int(intel.get("priority_bonus") or 0)
    return score


def _best_write_target(company: dict, intel: dict | None) -> str:
    if intel and isinstance(intel.get("write_first_to"), dict):
        target = intel["write_first_to"]
        name = str(target.get("name") or "").strip()
        role = str(target.get("role") or "").strip()
        if name and role:
            return f"{name} ({role})"
        if name:
            return name
    emails = _unique_strings(list((company.get("contacts") or {}).get("emails") or []))
    named = [email for email in emails if _is_named_email(email)]
    if named:
        return named[0]
    if emails:
        return emails[0]
    return "Need named buyer"


def _route_summary(company: dict, intel: dict | None) -> str:
    if intel and isinstance(intel.get("write_first_to"), dict):
        route = str(intel["write_first_to"].get("route") or "").strip()
        if route:
            return route
    if company.get("entry_route"):
        return str(company.get("entry_route"))
    emails = _unique_strings(list((company.get("contacts") or {}).get("emails") or []))
    if any(_is_named_email(email) for email in emails):
        return "named-email-first"
    return "brand-route-first"


def _fallback_emails(company: dict, intel: dict | None) -> list[str]:
    emails = _unique_strings(list((company.get("contacts") or {}).get("emails") or []))
    intel_emails: list[str] = []
    if intel:
        for person in _listify(intel.get("person_candidates")):
            if isinstance(person, dict):
                intel_emails.append(str(person.get("email") or ""))
    merged = _unique_strings([*intel_emails, *emails])
    named = [email for email in merged if _is_named_email(email)]
    generic = [email for email in merged if not _is_named_email(email)]
    return [*named, *generic][:5]


def _company_urls(company: dict, intel: dict | None) -> list[str]:
    urls = []
    urls.extend(_listify(company.get("blueprint_brand_urls")))
    urls.extend(_listify(company.get("blueprint_urls")))
    contacts = company.get("contacts") or {}
    for key in ("website", "career", "hr_landing"):
        if contacts.get(key):
            value = str(contacts[key]).strip()
            if value and not value.startswith("http"):
                value = f"https://{value}"
            urls.append(value)
    if intel:
        urls.extend(_listify(intel.get("proof_urls")))
        for route in _listify(intel.get("public_routes")):
            if isinstance(route, dict):
                urls.append(str(route.get("url") or ""))
    return _unique_strings(urls)


def _wave_for_rank(rank: int) -> str:
    if rank <= 5:
        return "wave_1"
    if rank <= 8:
        return "wave_2"
    return "wave_3"


def _build_target(company: dict, rank: int) -> dict:
    brand_key = _normalize_brand_key(company.get("name") or "")
    intel = PUBLIC_INTEL.get(brand_key) or {}
    score = _target_score(company, intel)
    return {
        "rank": rank,
        "wave": _wave_for_rank(rank),
        "brand": company.get("name"),
        "segment": company.get("segment"),
        "nsx_fit": int(company.get("nsx_fit") or 0),
        "priority_score": score,
        "why_now": str(intel.get("why_now") or company.get("signal_reason") or company.get("note") or "").strip(),
        "best_first_write_to": _best_write_target(company, intel),
        "recommended_entry_route": _route_summary(company, intel),
        "angle": str(company.get("angle") or "").strip(),
        "fallback_emails": _fallback_emails(company, intel),
        "person_candidates": _listify(intel.get("person_candidates")),
        "public_routes": _listify(intel.get("public_routes")),
        "proof_urls": _company_urls(company, intel),
        "next_gap": str(intel.get("next_gap") or "").strip(),
        "next_search_queries": _listify(intel.get("next_search_queries")),
        "source_blueprint_urls": _unique_strings(_listify(company.get("blueprint_urls"))),
    }


def build_theblueprint_people_targets_payload(shortlist_payload: dict, *, top_n: int = 10) -> dict:
    companies = list(shortlist_payload.get("companies") or [])
    scored: list[tuple[dict, int]] = []
    for company in companies:
        brand_key = _normalize_brand_key(company.get("name") or "")
        intel = PUBLIC_INTEL.get(brand_key)
        scored.append((company, _target_score(company, intel)))
    scored.sort(
        key=lambda item: (
            item[1],
            int(item[0].get("nsx_fit") or 0),
            str(item[0].get("name") or "").casefold(),
        ),
        reverse=True,
    )
    selected = [company for company, _ in scored[: max(top_n, 1)]]
    targets = [_build_target(company, index) for index, company in enumerate(selected, start=1)]

    wave_counts: dict[str, int] = {}
    for target in targets:
        wave = str(target.get("wave") or "")
        wave_counts[wave] = wave_counts.get(wave, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_from": str(shortlist_payload.get("generated_from") or "inputs/theblueprint_career_hiring.yaml"),
        "generated_from_shortlist": "inputs/theblueprint_career_hiring.yaml",
        "summary": {
            "shortlist_company_count": len(companies),
            "targets_count": len(targets),
            "wave_counts": wave_counts,
        },
        "heuristic": {
            "search_order": [
                "lock why-now signal",
                "find named buyer by role",
                "search person + brand in open web",
                "expand via Instagram bio",
                "expand via Telegram profile or channel",
                "close with official site and email trail",
            ],
            "default_priority": [
                "segment C and D with founder/person route",
                "segment B with named marketing or PR owner",
                "segment E only with clear named buyer or strong route",
            ],
        },
        "targets": targets,
    }


def load_yaml_payload(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_people_targets_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# The Blueprint stage-2 people targets",
        "# Auto-generated from the reduced shortlist plus public-route heuristics.",
        "# Focus: who to contact first, through which route, and what still needs confirmation.",
        "",
    ]
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100)
    path.write_text("\n".join(header) + body, encoding="utf-8")


def write_people_targets_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload.get("summary") or {}
    lines = [
        "# The Blueprint People Targets Report",
        "",
        "Source shortlist: `inputs/theblueprint_career_hiring.yaml`",
        f"Snapshot date: `{datetime.now(timezone.utc).date().isoformat()}`",
        "",
        "## Snapshot",
        "",
        f"- Shortlist companies scanned: `{summary.get('shortlist_company_count', 0)}`",
        f"- Outreach-ready targets in this pass: `{summary.get('targets_count', 0)}`",
        f"- Wave split: `{summary.get('wave_counts', {})}`",
        "",
        "## Who To Write First",
        "",
    ]

    for target in payload.get("targets") or []:
        lines.extend(
            [
                f"### {target['rank']}. {target['brand']}",
                "",
                f"- Segment: `{target.get('segment')}`",
                f"- Wave: `{target.get('wave')}`",
                f"- Score: `{target.get('priority_score')}`",
                f"- Write first to: `{target.get('best_first_write_to')}`",
                f"- Why now: {target.get('why_now')}",
                f"- Route: {target.get('recommended_entry_route')}",
            ]
        )
        if target.get("angle"):
            lines.append(f"- Pitch angle: {target.get('angle')}")
        if target.get("fallback_emails"):
            lines.append(f"- Fallback emails: {', '.join(target['fallback_emails'])}")
        if target.get("next_gap"):
            lines.append(f"- Current gap: {target.get('next_gap')}")
        if target.get("next_search_queries"):
            lines.append(f"- Next search queries: {', '.join(target['next_search_queries'])}")

        person_candidates = target.get("person_candidates") or []
        if person_candidates:
            lines.extend(["", "Primary people/routes:"])
            for person in person_candidates:
                if not isinstance(person, dict):
                    continue
                routes = _unique_strings(
                    [
                        person.get("email"),
                        person.get("instagram_url"),
                        person.get("telegram_url"),
                    ]
                )
                route_text = ", ".join(routes) if routes else "route not locked yet"
                lines.append(
                    f"- {person.get('name')} — {person.get('role')} | `{person.get('confidence')}` | {route_text}"
                )

        public_routes = target.get("public_routes") or []
        if public_routes:
            lines.extend(["", "Official/public routes:"])
            for route in public_routes:
                if not isinstance(route, dict):
                    continue
                lines.append(
                    f"- {route.get('label')} ({route.get('platform')}) — {route.get('url')} | `{route.get('confidence')}`"
                )

        proof_urls = _unique_strings(list(target.get("proof_urls") or []))[:8]
        if proof_urls:
            lines.extend(["", "Proof URLs:"])
            for url in proof_urls:
                lines.append(f"- {url}")
        lines.append("")

    lines.extend(
        [
            "## Search Logic",
            "",
            "1. Start from the `why now` trigger, not the platform.",
            "2. Lock one buyer name or one bridge contact before searching socials.",
            "3. Use Instagram only after the person identity is narrowed.",
            "4. If Instagram gives Telegram, inspect Telegram before guessing email patterns.",
            "5. Use the site/footer last to close the route, not as the first step.",
        ]
    )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
