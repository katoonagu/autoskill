# Browser Automation Runtime

This project now focuses on a multi-agent control plane for brand discovery and outreach operations.

## Active Modules

- `automation/modules/instagram_brand_search/`
- `automation/modules/subagents/`
- `automation/modules/brand_intelligence/`
- `automation/modules/outreach_planning/`
- `automation/modules/conversation/`
- `automation/modules/feedback_validation/`

## Browser Profiles

- `353` -> Discovery primary
- `345` -> Shared browser research
- `337` -> Conversation primary

The logical agents are no longer forced to own one browser profile each. Browser access is now a backend capability managed by `profile_pool.yaml`.

## Control-Plane Capabilities

- `Brand Intelligence` runs live web research through ranked search results, fetched page summaries, and a persisted `web_research.json` artifact per brand.
- `Conversation` is split into `prepare_draft` and `send_message`; the send path requires approval plus a leased conversation profile.
- `Validation` remains a non-browser downstream worker unless a future task explicitly requires browser access.

## Shared Runtime Pieces

- `automation/config.py`
- `automation/adspower.py`
- `automation/browser.py`
- `automation/human.py`
- `automation/artifacts.py`
- `automation/control_plane/`
- `automation/agents/contracts/`
- `automation/agents/profile_pool.yaml`

## Design Rules

- logical agents are separate from browser backends
- one browser profile is leased only when a task actually requires browser access
- keep operational state separate from knowledge memory
- use `LLM Wiki` for shared long-term memory
- keep raw evidence in outputs and artifacts
- keep human approval for any writing / messaging agent by default
- move work through task/approval contracts instead of ad-hoc script chaining

## Key Docs

- [Agent architecture](automation/agents/architecture.md)
- [Agent registry](automation/agents/registry.yaml)
- [LLM Wiki architecture](automation/agents/llm_wiki.md)
- [Task contracts](automation/agents/contracts/task_types.yaml)
- [Routing rules](automation/agents/contracts/routing_rules.yaml)
- [Profile pool](automation/agents/profile_pool.yaml)
- [Instagram brand search plan](automation/modules/instagram_brand_search/plan.md)
- [Instagram brand search job config](automation/modules/instagram_brand_search/job.yaml)
- [Browser subagents config](automation/modules/subagents/job.yaml)

## Legacy

The removed `genaipro / genai` workflow is archived in:

- [archive/genaipro_legacy](/c:/Users/occult/Desktop/auto/autoskill/archive/genaipro_legacy)
