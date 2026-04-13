from __future__ import annotations

import json


def build_media_analysis_prompt(*, media_payload: dict) -> str:
    return "\n".join(
        [
            "Вы — Media Intelligence layer для проекта Autoskill.",
            "Нужно оценить recent media context бренда и creator-brand fit.",
            "Верните только JSON по заданной schema.",
            "Правила:",
            "- comments считать слабым сигналом",
            "- не делать сильных выводов о качестве бренда только из комментариев",
            "- выделять tone, recurring themes, recurring requests, creator style, integration fit",
            "- use_as_signal и do_not_use_as_signal должны быть короткими и практическими",
            "",
            "<media_payload>",
            json.dumps(media_payload, ensure_ascii=False, indent=2),
            "</media_payload>",
        ]
    )
