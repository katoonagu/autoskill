from __future__ import annotations

import json


def build_brand_arbiter_prompt(*, evidence_bundle: dict, media_report: dict | None = None) -> str:
    return "\n".join(
        [
            "Ты — Brand Arbiter для проекта Autoskill.",
            "Твоя задача: оценить бренд-кейс по структурированным данным и вернуть только JSON.",
            "Формат мышления должен следовать схеме State -> Criteria -> Analysis -> Verdict, но в ответе нужен только JSON по заданной schema.",
            "Оцени кейс по критериям:",
            "- Business legitimacy",
            "- Collab evidence",
            "- Creator fit",
            "- Offerability",
            "- Risk",
            "- Evidence strength",
            "- Timing / why now",
            "Правила:",
            "- Не галлюцинируй данные, которых нет.",
            "- Если evidence слабые, верни need_more_research=true.",
            "- Если есть существенные риски или конфликт сигналов, recommended_action должно быть validate.",
            "- media_enrichment_required=true только если дополнительные media signals реально помогут улучшить решение.",
            "- what_not_to_say должен быть практическим списком запретов для writer-а.",
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
