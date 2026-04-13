from __future__ import annotations

import json


def build_brand_arbiter_prompt(*, evidence_bundle: dict, media_report: dict | None = None, policy: dict | None = None) -> str:
    return "\n".join(
        [
            "Вы — Brand Arbiter для проекта Autoskill.",
            "Ваша задача: оценить бренд-кейс по структурированным данным и вернуть только JSON.",
            "Внутренне следуйте схеме State -> Criteria -> Analysis -> Verdict, но в ответе нужен только JSON по заданной schema.",
            "Оцените кейс по критериям:",
            "- Business legitimacy",
            "- Collab evidence",
            "- Creator fit",
            "- Offerability",
            "- Risk",
            "- Evidence strength",
            "- Timing / why now",
            "Правила:",
            "- Не галлюцинируйте данные, которых нет.",
            "- Если evidence слабые, верните need_more_research=true.",
            "- Если confidence=low и evidence_strength=weak, по умолчанию не разрешайте verdict=plan_outreach.",
            "- Исключение: если кейс подпадает под instagram-native exception из policy и не выглядит рискованным, plan_outreach допустим.",
            "- Если есть существенные риски или конфликт сигналов, recommended_action должно быть validate.",
            "- media_enrichment_required=true только если дополнительные media signals реально помогут улучшить решение.",
            "- what_not_to_say должен быть практическим списком запретов для writer-а.",
            "- Если brand_follower_count >= threshold ultra_premium_policy, пометьте кейс как ultra_premium и добавьте special_handling.",
            "",
            "<creator_policy>",
            json.dumps(policy or {}, ensure_ascii=False, indent=2),
            "</creator_policy>",
            "",
            "<evidence_bundle>",
            json.dumps(evidence_bundle, ensure_ascii=False, indent=2),
            "</evidence_bundle>",
            "",
            "<media_report>",
            json.dumps(media_report or {}, ensure_ascii=False, indent=2),
            "</media_report>",
        ]
    )
