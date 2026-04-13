from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


OVERRIDES: dict[str, dict[str, object]] = {
    "boohoo": {
        "brand_name": "boohoo",
        "brand_strengths": [
            "Это крупный международный fashion-бренд с многомиллионной аудиторией и сильной узнаваемостью.",
            "Есть заметное официальное присутствие в сети.",
            "Кейс полезно сохранить в отдельном product/service track.",
        ],
        "brand_weaknesses": [
            "Для стандартного outreach под Farida бренд выглядит слишком большим и корпоративным.",
            "Не просматривается простой заход для обычного manager outreach.",
            "Быстрый DM-подход здесь вряд ли даст качественный коммерческий результат.",
        ],
        "risk_flags": [
            "Ultra-premium / enterprise-sized brand.",
            "Кейс логичнее вести в separate_track_production, а не в обычном outreach-потоке.",
        ],
        "why_this_brand": "Это сильный бренд, но он не относится к обычному mid/premium outreach-пулу и требует другого сценария работы.",
        "why_now": "Полезно сохранить кейс в базе как потенциальный production-контакт, а не как прямой кандидат на стандартный рекламный outreach.",
        "what_not_to_say": [
            "Не предлагать небольшой outreach как будто это обычный Instagram-native бренд.",
            "Не обещать быстрый и простой запуск.",
            "Не позиционировать кейс как quick win.",
        ],
        "recommended_angle": "Не предлагать стандартный outreach; сохранить бренд в отдельном треке для более сильного коммерческого предложения.",
    },
    "mercury_russia": {
        "brand_name": "Mercury",
        "brand_strengths": [
            "Сильный Instagram-native бренд с 135 000 подписчиков и заметным брендовым присутствием.",
            "Категория jewelry_accessories входит в число приоритетных для сотрудничества.",
            "Есть creator-source сигналы, на которые можно опереться в первом коммерческом сообщении.",
        ],
        "brand_weaknesses": [
            "Внешняя легитимация бренда через сайт и reviews ограничена.",
            "Кейс пока держится на Instagram-контексте и не имеет плотного web footprint.",
            "Нужна аккуратная формулировка оффера без лишних claims и обещаний.",
        ],
        "risk_flags": [
            "Основной сигнал идёт из Instagram-контекста, а не из широкого web footprint.",
        ],
        "why_this_brand": "Mercury выглядит как сильный jewelry/fashion Instagram-native бренд, который визуально сочетается с образом Farida и её аудиторией.",
        "why_now": "Есть creator-контекст, на который можно опереться, и бренд подходит для имиджевой рекламной интеграции в формате Reels.",
        "what_not_to_say": [
            "Не обещать performance-результаты.",
            "Не ссылаться на неподтверждённые внешние отзывы или reviews.",
            "Не писать, что бренд везде присутствует за пределами Instagram, если это не подтверждено.",
        ],
        "recommended_angle": "Имиджевая fashion/jewelry интеграция через Reels с акцентом на женскую аудиторию, рекомендации и image placement.",
        "research_gaps": [
            "Контакт и юридические данные не подтверждены; для старта это не блокирует аккуратный DM.",
        ],
    },
    "vilavi_london": {
        "brand_name": "vilavi • bold statement jewellery",
        "brand_strengths": [
            "Jewelry category входит в число приоритетных и хорошо совпадает с тематикой сотрудничества.",
            "Есть найденный email-контакт для прямого outreach.",
            "Instagram-профиль выглядит живым и понятным для statement jewellery.",
        ],
        "brand_weaknesses": [
            "Нет подтверждённого сайта.",
            "Внешняя web-легитимация ограничена.",
            "Пока мало creator-signals, поэтому заход должен быть аккуратным.",
        ],
        "risk_flags": [
            "Instagram-native кейс без сильного внешнего подтверждения.",
        ],
        "why_this_brand": "Категория statement jewelry хорошо сочетается с fashion/lifestyle образом Farida и даёт понятную основу для рекламной интеграции.",
        "why_now": "Это хороший warm outreach-кейс: понятная категория, найденный контакт и формат, который можно упаковать под Reels и визуальный контент.",
        "what_not_to_say": [
            "Не обещать прямые продажи.",
            "Не подавать бренд как ultra-premium или международного гиганта.",
            "Не перегружать первое письмо деталями внутреннего ресерча.",
        ],
        "recommended_angle": "Имиджевая Reels-интеграция для statement jewelry с упором на стиль, визуальность и женский fashion-контекст.",
        "research_gaps": [
            "Желательно со временем собрать ещё 1–2 внешних brand signals, но это не блокирует первый outreach.",
        ],
    },
    "chertovski_official": {
        "brand_name": "CHERTOVSKI | Premium Womenswear",
        "brand_strengths": [
            "Категория premium womenswear хорошо сочетается с fashion-позиционированием Farida.",
            "Есть creator-контекст и визуальный fashion-матч.",
            "Понятный товарный профиль и женская premium-эстетика.",
        ],
        "brand_weaknesses": [
            "Слишком маленький Instagram-профиль для уверенного brand outreach: 546 подписчиков.",
            "Нет сайта, контактов и сильной внешней легитимации бренда.",
            "Кейс пока держится на одном creator-source и слабом общем сигнале бренда.",
        ],
        "risk_flags": [
            "Слишком мало внешних evidence.",
            "Кейс лучше сначала отправить в validate, а не в прямой outreach.",
        ],
        "why_this_brand": "Бренд выглядит визуально близким к premium fashion-эстетике Farida, но пока не подтверждён как устойчивый коммерческий бренд для outreach.",
        "why_now": "Отдельного timing hook сейчас нет; сначала нужен более сильный слой валидации и подтверждения бренда.",
        "what_not_to_say": [
            "Не позиционировать бренд как крупного игрока.",
            "Не делать вид, что у бренда уже есть подтверждённый масштаб.",
            "Не предлагать рекламную интеграцию так, будто кейс уже полностью готов к продаже.",
        ],
        "recommended_angle": "Пока не предлагать рекламу напрямую; сначала подтвердить, что это полноценный premium womenswear бренд, а не маленькое atelier-направление.",
        "research_gaps": [
            "Нужен дополнительный поиск по легитимации бренда вне Instagram.",
            "Нужна проверка, есть ли подтверждённые контакты или сайт у бренда.",
        ],
    },
    "brucestudios": {
        "brand_name": "brucestudios",
        "brand_strengths": [
            "Есть подтверждённый сайт/help-center и понятный digital product/service footprint.",
            "Категория wellness/fitness допустима в рамках policy.",
            "Есть route для website-contact обращения.",
        ],
        "brand_weaknesses": [
            "Fit с Farida заметно слабее, чем у fashion, beauty или jewelry кейсов.",
            "Текущий продуктовый контекст требует более аккуратной коммерческой упаковки.",
            "Пока не видно сильного lifestyle-match, который сам по себе убедительно свяжет бренд с Farida.",
        ],
        "risk_flags": [
            "Категория не приоритетная.",
            "Нужен более ясный коммерческий angle перед outreach.",
        ],
        "why_this_brand": "Wellness-направление допустимо, но визуальный fit с образом Farida слабее, чем у более очевидных fashion/beauty кейсов.",
        "why_now": "Кейс можно держать как потенциальный, но сначала нужен более точный lifestyle use case и более сильный коммерческий угол.",
        "what_not_to_say": [
            "Не приравнивать fitness-service к fashion/lifestyle match без доказательств.",
            "Не предлагать рекламу без чёткого angle.",
            "Не говорить, что аудитория Farida автоматически релевантна любому wellness-продукту.",
        ],
        "recommended_angle": "Пока не продавать напрямую; сначала собрать более сильный lifestyle/wellness angle и premium self-care framing.",
        "research_gaps": [
            "Нужна конкретика, почему это должно сработать именно на аудитории Farida.",
            "Нужен более сильный commercial hook для wellness-category.",
        ],
    },
    "ohtapark": {
        "brand_name": "Всесезонный курорт «Охта Парк»",
        "brand_strengths": [
            "Есть базовый travel/leisure fit и понятный визуальный контекст для creator.",
        ],
        "brand_weaknesses": [
            "Недостаточно выраженного creator-контекста для прямого outreach.",
        ],
        "risk_flags": [
            "Мало внешних signals и ограниченный набор review-признаков.",
        ],
        "why_this_brand": "Есть общий fit по leisure-направлению, но кейс пока выглядит как слабая outreach-гипотеза.",
        "why_now": "Сейчас лучше не форсировать сообщение бренду, пока не появится более сильный контекст или timing.",
        "what_not_to_say": [
            "Не преувеличивать высокий коммерческий fit без дополнительного evidence.",
        ],
        "recommended_angle": "Пока не предлагать активный outreach; сначала усилить доказательную базу.",
        "research_gaps": [
            "Нужны дополнительные сигналы по бренду и контакту.",
            "Желательно добавить creator или review signals.",
        ],
    },
}


def _build_report(packet: dict, *, brand_handle: str) -> str:
    criteria_lines = [
        "- Business legitimacy",
        "- Collab evidence",
        "- Creator fit",
        "- Offerability",
        "- Risk",
        "- Evidence strength",
        "- Timing / why now",
    ]
    analysis_lines: list[str] = []
    for key in ("brand_strengths", "brand_weaknesses", "risk_flags", "research_gaps"):
        values = packet.get(key) or []
        if values:
            analysis_lines.append(f"### {key}")
            analysis_lines.extend(f"- {item}" for item in values)
            analysis_lines.append("")
    return "\n".join(
        [
            f"# Brand Arbiter @{brand_handle}",
            "",
            "## State",
            f"- Brand name: {packet.get('brand_name') or brand_handle}",
            f"- Confidence: {packet.get('confidence')}",
            f"- Evidence strength: {packet.get('evidence_strength')}",
            f"- Provider: {packet.get('llm_provider')}",
            f"- Media report attached: {'yes' if packet.get('media_report_path') else 'no'}",
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
            f"- Verdict: {packet.get('verdict')}",
            f"- Recommended action: {packet.get('recommended_action')}",
            f"- Recommended channel: {packet.get('recommended_channel')}",
            f"- Recommended angle: {packet.get('recommended_angle')}",
            f"- Why this brand: {packet.get('why_this_brand')}",
            f"- Why now: {packet.get('why_now')}",
            "",
        ]
    )


def _clean_followers_text(stats: dict) -> str:
    followers = int(stats.get("brand_follower_count") or stats.get("follower_count") or 0)
    if followers <= 0:
        return str(stats.get("brand_followers_text") or "")
    parts = [f"{followers:,} followers".replace(",", " ")]
    raw = str(stats.get("brand_followers_text") or "")
    following_match = None
    posts_match = None
    import re
    following_match = re.search(r"(\d[\d\s,]*)\s+following", raw, re.IGNORECASE)
    posts_match = re.search(r"(\d[\d\s,]*)\s+posts", raw, re.IGNORECASE)
    if following_match:
        parts.append(f"{following_match.group(1).replace(',', ' ').strip()} following")
    if posts_match:
        parts.append(f"{posts_match.group(1).replace(',', ' ').strip()} posts")
    return " / ".join(parts)


def _repair_handle(handle: str) -> None:
    packet_path = PROJECT_ROOT / "output" / "brand_arbiter" / handle / "intelligence_packet.json"
    report_path = PROJECT_ROOT / "output" / "brand_arbiter" / handle / "arbiter_report.md"
    if not packet_path.exists():
        raise FileNotFoundError(packet_path)

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    override = OVERRIDES[handle]
    packet.update(override)

    evidence_bundle_path = PROJECT_ROOT / "output" / "brand_intelligence" / handle / "evidence_bundle.json"
    if evidence_bundle_path.exists():
        evidence_bundle = json.loads(evidence_bundle_path.read_text(encoding="utf-8"))
        mention_stats = dict(evidence_bundle.get("mention_statistics") or {})
        if mention_stats:
            packet["supporting_stats"] = dict(packet.get("supporting_stats") or {})
            for key, value in mention_stats.items():
                packet["supporting_stats"][key] = value
    packet["supporting_stats"] = dict(packet.get("supporting_stats") or {})
    packet["supporting_stats"]["brand_followers_text"] = _clean_followers_text(packet["supporting_stats"])

    report_text = _build_report(packet, brand_handle=str(packet.get("brand_handle") or handle))
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_text + "\n", encoding="utf-8-sig")

    manual_packet_path = PROJECT_ROOT / "output" / "supervisor" / "codex_manual_packets" / f"codex_manual__brand_arbiter__{handle}.json"
    if manual_packet_path.exists():
        manual_packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    for handle in OVERRIDES:
        _repair_handle(handle)
        print(f"Repaired: {handle}")


if __name__ == "__main__":
    main()
