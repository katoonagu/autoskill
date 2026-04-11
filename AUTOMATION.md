# Browser Automation Runtime

This project now focuses on a multi-agent browser automation runtime for brand discovery and outreach operations.

## Active Modules

- `automation/modules/instagram_brand_search/`
- `automation/modules/subagents/`
- `automation/modules/brand_intelligence/`
- `automation/modules/outreach_planning/`
- `automation/modules/conversation/`
- `automation/modules/feedback_validation/`

## Active Profiles

- `353` -> Discovery
- `345` -> Brand Intelligence
- `346` -> Outreach Planning
- `337` -> Conversation
- `333` -> Feedback / Validation

## Shared Runtime Pieces

- `automation/config.py`
- `automation/adspower.py`
- `automation/browser.py`
- `automation/human.py`
- `automation/artifacts.py`

## Design Rules

- one active browser agent per dedicated AdsPower profile
- keep operational state separate from knowledge memory
- use `LLM Wiki` for shared long-term memory
- keep raw evidence in outputs and artifacts
- keep human approval for any writing / messaging agent by default

## Key Docs

- [Agent architecture](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/architecture.md)
- [Agent registry](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/registry.yaml)
- [LLM Wiki architecture](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/llm_wiki.md)
- [Instagram brand search plan](/c:/Users/occult/Desktop/auto/autoskill/automation/modules/instagram_brand_search/plan.md)
- [Instagram brand search job config](/c:/Users/occult/Desktop/auto/autoskill/automation/modules/instagram_brand_search/job.yaml)
- [Browser subagents config](/c:/Users/occult/Desktop/auto/autoskill/automation/modules/subagents/job.yaml)

## Legacy

The removed `genaipro / genai` workflow is archived in:

- [archive/genaipro_legacy](/c:/Users/occult/Desktop/auto/autoskill/archive/genaipro_legacy)
