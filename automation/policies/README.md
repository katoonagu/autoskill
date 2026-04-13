# Policy Map

Основной policy-layer проекта под Farida Shirinova.

Source of truth:
- [farida_shirinova.yaml](./farida_shirinova.yaml) — машинно-читаемая политика брендов, тональности, CTA и сегментации.
- [farida_shirinova.md](./farida_shirinova.md) — краткое человекочитаемое описание policy.
- [__init__.py](./__init__.py) — загрузчик policy в runtime.

Где policy реально применяется:
- [..\llm\prompts\brand_arbiter.py](../llm/prompts/brand_arbiter.py) — LLM prompt для `Brand Arbiter`.
- [..\llm\schemas.py](../llm/schemas.py) — schema структурированного arbiter/media output.
- [..\modules\brand_intelligence\worker.py](../modules/brand_intelligence/worker.py) — collector, supporting stats, follower count, `ultra_premium`.
- [..\modules\brand_arbiter\worker.py](../modules/brand_arbiter/worker.py) — heuristic arbiter, Instagram-native exception, verdict logic.
- [..\modules\outreach_planning\worker.py](../modules/outreach_planning/worker.py) — planning и сегментация для downstream offer.
- [..\modules\conversation\style_policies.py](../modules/conversation/style_policies.py) — tone per channel.
- [..\modules\conversation\worker.py](../modules/conversation/worker.py) — реальный текст оффера и draft generation.

Главные policy-блоки:
- brand categories and exclusions
- instagram-native exception
- red flags and validate/discard rules
- offer strategy and value proposition
- metrics usage policy
- channel tone policy
- CTA policy
- ultra premium segmentation
