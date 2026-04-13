from __future__ import annotations


UNIFIED_CTA = (
    "Если это направление Вам интересно, готов направить актуальную статистику "
    "и 2–3 идеи интеграции под Ваш продукт."
)


CHANNEL_STYLE_POLICIES = {
    "instagram_dm": {
        "salutation": "Здравствуйте!",
        "tone": "laconic_polite_semiformal",
        "goal": "кратко и по делу предложить рекламную интеграцию",
        "cta": UNIFIED_CTA,
    },
    "email": {
        "salutation": "Здравствуйте!",
        "tone": "strict_business_structured",
        "goal": "деловое предложение по рекламному размещению",
        "cta": UNIFIED_CTA,
    },
    "website_contact": {
        "salutation": "Здравствуйте!",
        "tone": "official",
        "goal": "официально предложить рекламное сотрудничество",
        "cta": UNIFIED_CTA,
    },
}


def get_channel_style_policy(channel: str) -> dict[str, str]:
    normalized = str(channel or "").strip().lower()
    return dict(CHANNEL_STYLE_POLICIES.get(normalized) or CHANNEL_STYLE_POLICIES["instagram_dm"])
