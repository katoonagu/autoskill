"""Build one consolidated report for The Blueprint outreach work."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .text_utils import load_yaml_utf8


SEGMENT_LABELS = {
    "B": "strong brand / retail",
    "C": "founder-led DTC / fashion / beauty",
    "D": "HoReCa / restaurant",
    "E": "tech / SaaS / digital",
}

NOISE_HOST_MARKERS = (
    "zhihu.com",
    "baidu.com",
    "reddit.com",
    "support.google.com",
    "accounts.google.com",
    "mail.google.com",
    "play.google.com",
    "gemini.google.com",
    "support.microsoft.com",
    "answers.microsoft.com",
    "outlook.live.com",
    "outlook.office.com",
    "stackoverflow.com",
    "youtube.com",
    "github.com",
    "facebook.com",
    "orange.fr",
    "studio.se",
    "sparxmaths.com",
    "scratch.mit.edu",
    "premierinn.com",
    "health.usnews.com",
    "clinicadvisor.com",
    "yourskinvision.com",
    "nbcnews.com",
    "chatgpt.com",
    "openai.com",
    "waygroup.se",
    "community.swisscom.ch",
    "forum.vivaldi.net",
    "superherohype.com",
    "otvet.mail.ru",
)

TRUSTED_HOST_MARKERS = (
    "theblueprint.ru",
    "instagram.com",
    "t.me",
    "telegram.me",
    "vc.ru",
    "cossa.ru",
    "sostav.ru",
    "adindex.ru",
    "forbes.ru",
    "rbc.ru",
    "vedomosti.ru",
    "moskvichmag.ru",
)


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


def _normalize_brand_key(value: str) -> str:
    return " ".join(str(value or "").replace("’", "'").replace("`", "'").casefold().split())


def _domain(url: str) -> str:
    return urlparse(str(url or "")).netloc.lower()


def _host_is_noise(host: str) -> bool:
    return any(marker in host for marker in NOISE_HOST_MARKERS)


def _host_is_trusted(host: str) -> bool:
    return any(marker in host for marker in TRUSTED_HOST_MARKERS)


def _first_sentence(text: str) -> str:
    value = " ".join(str(text or "").split())
    if not value:
        return ""
    for marker in (". ", "! ", "? "):
        if marker in value:
            return value.split(marker, 1)[0].strip(" .!?") + "."
    return value


def _person_route_strength(target: dict, route: dict | None) -> str:
    if route and route.get("status") == "resolved_person_route":
        return "strong"
    if route and route.get("status") == "resolved_brand_route":
        return "medium"
    if route and route.get("status") == "partial":
        return "medium"

    for person in _listify(target.get("person_candidates")):
        if not isinstance(person, dict):
            continue
        if person.get("instagram_url") or person.get("telegram_url") or person.get("email"):
            return "strong" if str(person.get("confidence") or "") == "high" else "medium"
    if target.get("fallback_emails") or target.get("public_routes"):
        return "medium"
    return "weak"


def _verdict(target: dict, route: dict | None) -> str:
    strength = _person_route_strength(target, route)
    if strength == "strong":
        return "WRITE NOW"
    if strength == "medium":
        return "ENRICH 10-15 MIN, THEN WRITE"
    return "HOLD / LOW CONFIDENCE"


def _default_offer(segment: str, brand: str) -> str:
    if segment == "C":
        return f"короткий launch-пакет для {brand}: 1 hero video + 4-6 вертикалей под Instagram / Telegram / VK"
    if segment == "D":
        return f"серия vertical reels для {brand} + быстрый AI-джингл / саунд-идея под social и заведение"
    if segment == "E":
        return f"brand/product narrative для {brand} + набор вертикальных cutdown-роликов под digital-каналы"
    return f"брендовый seasonal-пакет для {brand}: имиджевый ролик + вертикальные вырезки под performance и social"


def _build_pitch(target: dict) -> list[str]:
    brand = str(target.get("brand") or "")
    person = str(target.get("best_first_write_to") or "buyer")
    why_now = _first_sentence(str(target.get("why_now") or ""))
    angle = str(target.get("angle") or "").strip()
    offer = angle if angle else _default_offer(str(target.get("segment") or ""), brand)
    subject = f"{brand}: идея под текущий hiring / launch signal"
    opener = f"Увидел, что у вас {why_now.lower()}" if why_now else f"Увидел свежий сигнал по {brand} в The Blueprint."
    body = f"Для {brand} здесь логично предложить {offer}."
    cta = "Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона."
    return [
        f"Тема: {subject}",
        f"Открытие: {opener}",
        f"Оффер: {body}",
        f"CTA: {cta}",
        f"Кому: {person}",
    ]


def _trusted_urls(target: dict, route: dict | None) -> list[str]:
    urls = []
    urls.extend(_listify(target.get("proof_urls")))
    urls.extend(_listify(target.get("source_blueprint_urls")))
    if route:
        urls.extend(_listify(route.get("resolved_contact_urls")))
        urls.extend(_listify(route.get("resolved_instagrams")))
        urls.extend(_listify(route.get("resolved_telegrams")))
    cleaned: list[str] = []
    for url in _unique_strings(urls):
        host = _domain(url)
        if not host:
            continue
        if _host_is_trusted(host) or host.endswith(".ru"):
            cleaned.append(url)
    return cleaned[:10]


def _noise_urls(route: dict | None) -> list[str]:
    if not route:
        return []
    urls = []
    for url in _unique_strings(_listify(route.get("proof_urls"))):
        host = _domain(url)
        if host and _host_is_noise(host):
            urls.append(url)
    return urls[:8]


def _backup_routes(target: dict, route: dict | None) -> list[str]:
    result = []
    for person in _listify(target.get("person_candidates")):
        if not isinstance(person, dict):
            continue
        name = str(person.get("name") or "").strip()
        role = str(person.get("role") or "").strip()
        routes = _unique_strings(
            [
                person.get("instagram_url"),
                person.get("telegram_url"),
                person.get("email"),
            ]
        )
        if routes:
            result.append(f"{name} ({role}): {', '.join(routes)}")
    for route_item in _listify(target.get("public_routes")):
        if not isinstance(route_item, dict):
            continue
        label = str(route_item.get("label") or route_item.get("platform") or "route")
        url = str(route_item.get("url") or "").strip()
        if url:
            result.append(f"{label}: {url}")
    if route:
        emails = _unique_strings(_listify(route.get("resolved_emails")))
        if emails:
            result.append(f"Stage-3 emails: {', '.join(emails[:4])}")
    for email in _unique_strings(_listify(target.get("fallback_emails"))):
        result.append(f"Fallback email: {email}")
    return result[:8]


def _route_status_label(target: dict, route: dict | None) -> str:
    if route:
        return f"{route.get('status')} / {route.get('route_confidence')}"
    if target.get("person_candidates") or target.get("public_routes"):
        return "stage-2 only / not in current route snapshot"
    return "not resolved"


def _priority_value(priority: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(str(priority or "").lower(), 0)


def _segment_value(segment: str) -> int:
    return {"C": 4, "D": 3, "B": 2, "E": 1}.get(str(segment or ""), 0)


def _backlog_companies(shortlist_payload: dict, top_brands: set[str], route_map: dict[str, dict]) -> list[dict]:
    companies = []
    for company in shortlist_payload.get("companies") or []:
        if not isinstance(company, dict):
            continue
        if str(company.get("name") or "") in top_brands:
            continue
        companies.append(company)
    companies.sort(
        key=lambda item: (
            -int(item.get("nsx_fit") or 0),
            -_priority_value(str(item.get("priority") or "")),
            -_segment_value(str(item.get("segment") or "")),
            str(item.get("name") or "").casefold(),
        )
    )
    rows = []
    for company in companies:
        brand = str(company.get("name") or "")
        route = route_map.get(_normalize_brand_key(brand))
        rows.append(
            {
                "brand": brand,
                "segment": str(company.get("segment") or ""),
                "nsx_fit": int(company.get("nsx_fit") or 0),
                "priority": str(company.get("priority") or ""),
                "signal_reason": str(company.get("signal_reason") or ""),
                "route_state": _route_status_label({}, route),
            }
        )
    return rows


def _noise_brands(route_payload: dict) -> list[dict]:
    rows = []
    for item in route_payload.get("resolutions") or []:
        if not isinstance(item, dict):
            continue
        suspicious = _noise_urls(item)
        if len(suspicious) < 3:
            continue
        rows.append(
            {
                "brand": str(item.get("brand") or ""),
                "status": str(item.get("status") or ""),
                "noise_count": len(suspicious),
                "noise_hosts": _unique_strings(_domain(url) for url in suspicious),
            }
        )
    rows.sort(key=lambda item: (-int(item.get("noise_count") or 0), item["brand"].casefold()))
    return rows


def _noise_domain_summary(route_payload: dict) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in route_payload.get("resolutions") or []:
        if not isinstance(item, dict):
            continue
        for url in _noise_urls(item):
            host = _domain(url)
            if not host:
                continue
            counts[host] = counts.get(host, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:20]


def load_yaml_payload(path: Path) -> dict:
    return load_yaml_utf8(path)


def build_theblueprint_master_report_payload(
    shortlist_payload: dict,
    people_targets_payload: dict,
    route_payload: dict,
) -> dict:
    top_targets = list(people_targets_payload.get("targets") or [])
    top_target_map = {_normalize_brand_key(str(item.get("brand") or "")): item for item in top_targets}
    route_map = {_normalize_brand_key(str(item.get("brand") or "")): item for item in route_payload.get("resolutions") or []}

    detailed_targets = []
    for target in top_targets:
        brand_key = _normalize_brand_key(str(target.get("brand") or ""))
        route = route_map.get(brand_key)
        detailed_targets.append(
            {
                "brand": target.get("brand"),
                "wave": target.get("wave"),
                "rank": target.get("rank"),
                "segment": target.get("segment"),
                "priority_score": target.get("priority_score"),
                "why_now": target.get("why_now"),
                "best_first_write_to": target.get("best_first_write_to"),
                "recommended_entry_route": target.get("recommended_entry_route"),
                "angle": target.get("angle"),
                "next_gap": target.get("next_gap"),
                "next_search_queries": target.get("next_search_queries"),
                "route_snapshot": _route_status_label(target, route),
                "verdict": _verdict(target, route),
                "pitch_lines": _build_pitch(target),
                "backup_routes": _backup_routes(target, route),
                "trusted_urls": _trusted_urls(target, route),
                "potential_noise_urls": _noise_urls(route),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "archive_company_count": int((shortlist_payload.get("summary") or {}).get("archive_company_count") or 0),
            "shortlist_company_count": int((shortlist_payload.get("summary") or {}).get("selected_company_count") or 0),
            "segment_counts": (shortlist_payload.get("summary") or {}).get("segment_counts") or {},
            "top_targets_count": int((people_targets_payload.get("summary") or {}).get("targets_count") or 0),
            "wave_counts": (people_targets_payload.get("summary") or {}).get("wave_counts") or {},
            "route_snapshot": (route_payload.get("summary") or {}),
        },
        "heuristic": people_targets_payload.get("heuristic") or {},
        "top_targets": detailed_targets,
        "backlog": _backlog_companies(
            shortlist_payload,
            {str(item.get("brand") or "") for item in top_targets},
            route_map,
        ),
        "noise_brands": _noise_brands(route_payload),
        "noise_domains": _noise_domain_summary(route_payload),
    }


def write_theblueprint_master_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload.get("summary") or {}
    wave_counts = summary.get("wave_counts") or {}
    route_snapshot = summary.get("route_snapshot") or {}

    lines = [
        "# The Blueprint Outreach Master Report",
        "",
        "Этот файл сводит в одно место весь текущий pipeline по The Blueprint career:",
        "- full archive parser по career-разделу",
        "- shortlist reducer по сегментам B/C/D/E",
        "- stage-2 people targets",
        "- stage-3 route resolver",
        "- ручную пометку потенциального мусора в auto-search выдаче",
        "",
        f"Собрано: `{payload.get('generated_at')}`",
        "",
        "## Метод",
        "",
        "### Шаг 1. Полный сбор",
        "- Из career-архива The Blueprint берутся все brand pages и все вакансии брендов.",
        "- Затем архив схлопывается до company-level карточек: бренд, роли, вакансии, e-mail, источники.",
        "",
        "### Шаг 2. Редукция до рабочей shortlist",
        "- Оставляем только сегменты `B/C/D/E`.",
        "- Вырезаем media / culture / non-target сущности.",
        "- Оставляем только свежие marketing / PR / content сигналы.",
        "",
        "### Шаг 3. Приоритизация",
        "- Смотрим не на величину бренда, а на `why now`: свежий hiring, кадровая перестановка, запуск категории, founder-led доступность.",
        "- Для `C/D` приоритет person-first. Для `B` — person-first при наличии имени, иначе person + brand route. Для `E` — role-first.",
        "",
        "### Шаг 4. Person-route логика",
        "- Сначала фиксируем buyer по роли.",
        "- Потом ищем `ФИО + бренд` в открытом вебе.",
        "- Потом Instagram/Telegram/site/email trail.",
        "- Только после этого считаем, что маршрут контакта реально существует.",
        "",
        "### Шаг 5. Фильтр мусора",
        "- Если auto-search приносит `zhihu`, `baidu`, `reddit`, `support.google`, `youtube`, `stackoverflow` и похожий шум, эти результаты не считаются доказательством.",
        "- В детальных карточках ниже такие находки либо вырезаны, либо помечены как `potential noise`.",
        "",
        "## Snapshot",
        "",
        f"- Архив компаний: `{summary.get('archive_company_count', 0)}`",
        f"- Shortlist после фильтрации: `{summary.get('shortlist_company_count', 0)}`",
        f"- Разбивка по сегментам: `{summary.get('segment_counts', {})}`",
        f"- Активные top targets: `{summary.get('top_targets_count', 0)}`",
        f"- Wave split: `{wave_counts}`",
        f"- Текущий stage-3 snapshot: `{route_snapshot}`",
        "",
        "## Финальный порядок действий",
        "",
        "### Wave 1",
    ]

    for item in payload.get("top_targets") or []:
        if item.get("wave") != "wave_1":
            continue
        lines.append(f"- `{item.get('brand')}` — {item.get('verdict')} — {item.get('best_first_write_to')}")

    lines.extend(["", "### Wave 2"])
    for item in payload.get("top_targets") or []:
        if item.get("wave") != "wave_2":
            continue
        lines.append(f"- `{item.get('brand')}` — {item.get('verdict')} — {item.get('best_first_write_to')}")

    lines.extend(["", "### Wave 3"])
    for item in payload.get("top_targets") or []:
        if item.get("wave") != "wave_3":
            continue
        lines.append(f"- `{item.get('brand')}` — {item.get('verdict')} — {item.get('best_first_write_to')}")

    lines.extend(["", "## Детально: кому писать и что писать", ""])
    for item in payload.get("top_targets") or []:
        lines.extend(
            [
                f"### {item.get('rank')}. {item.get('brand')}",
                "",
                f"- Verdict: `{item.get('verdict')}`",
                f"- Segment: `{item.get('segment')}` ({SEGMENT_LABELS.get(str(item.get('segment') or ''), 'unknown')})",
                f"- Wave: `{item.get('wave')}`",
                f"- Score: `{item.get('priority_score')}`",
                f"- Почему сейчас: {item.get('why_now')}",
                f"- Кому писать первым: {item.get('best_first_write_to')}",
                f"- Вход: {item.get('recommended_entry_route')}",
                f"- Stage-3 snapshot: `{item.get('route_snapshot')}`",
            ]
        )
        if item.get("angle"):
            lines.append(f"- Pitch angle: {item.get('angle')}")
        if item.get("next_gap"):
            lines.append(f"- Текущий gap: {item.get('next_gap')}")

        lines.extend(["", "Что писать:"])
        for pitch_line in item.get("pitch_lines") or []:
            lines.append(f"- {pitch_line}")

        backup_routes = item.get("backup_routes") or []
        if backup_routes:
            lines.extend(["", "Что уже найдено:"])
            for route_line in backup_routes:
                lines.append(f"- {route_line}")

        trusted_urls = item.get("trusted_urls") or []
        if trusted_urls:
            lines.extend(["", "Доверенные ссылки:"])
            for url in trusted_urls[:8]:
                lines.append(f"- {url}")

        if item.get("next_search_queries"):
            lines.extend(["", "Если добивать ещё 10 минут:"])
            for query in _listify(item.get("next_search_queries"))[:6]:
                lines.append(f"- {query}")

        potential_noise = item.get("potential_noise_urls") or []
        if potential_noise:
            lines.extend(["", "Potential noise, не использовать как доказательство:"])
            for url in potential_noise[:6]:
                lines.append(f"- {url}")

        lines.append("")

    lines.extend(["## Backlog: хорошие бренды, но не первая десятка", ""])
    for item in payload.get("backlog") or []:
        lines.append(
            f"- `{item.get('brand')}` | seg `{item.get('segment')}` | nsx `{item.get('nsx_fit')}` | "
            f"priority `{item.get('priority')}` | route `{item.get('route_state')}` | {item.get('signal_reason')}"
        )

    lines.extend(["", "## Potential Мусор В Auto-Search", ""])
    lines.append("Эти бренды не обязательно плохие. Плохой именно auto-search хвост, который нельзя считать контактом без ручной проверки.")
    lines.append("")
    for item in payload.get("noise_brands") or []:
        lines.append(
            f"- `{item.get('brand')}` | status `{item.get('status')}` | noise `{item.get('noise_count')}` | "
            f"domains: {', '.join(item.get('noise_hosts') or [])}"
        )

    lines.extend(["", "### Наиболее частые шумные домены", ""])
    for host, count in payload.get("noise_domains") or []:
        lines.append(f"- `{host}` — `{count}`")

    lines.extend(
        [
            "",
            "## Что я считаю готовым к отправке прямо сейчас",
            "",
            "- `Don't Touch My Skin`",
            "- `Emka`",
            "- `Ushatava`",
            "- `2Mood`",
            "- `YuliaWave`",
            "",
            "## Что сначала бы ещё добил 10-15 минут",
            "",
            "- `Befree` — нужен прямой social-route Евгения Лагутина",
            "- `Finn Flare` — нужно имя buyer, а не только HR bridge",
            "- `Lamoda` — нужен owner private label / brand",
            "- `Bork` — нужен brand / PR owner вместо hiring bridge",
            "- `Бар «Ровесник»` — нужен личный route фаундера, а не только brand socials",
            "",
            "## Где смотреть сырые артефакты",
            "",
            "- `inputs/theblueprint_career_hiring.yaml` — shortlist на 81 бренд",
            "- `artifacts/company_contacts_enrichment/theblueprint_people_targets.yaml` — top-10 people targets",
            "- `artifacts/company_contacts_enrichment/theblueprint_route_resolutions.yaml` — stage-3 route snapshot",
        ]
    )

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

