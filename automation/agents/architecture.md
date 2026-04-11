# Agent Architecture

## Goal

Turn the project into a dedicated multi-agent operating model with:

- one browser-bound agent per AdsPower profile
- one shared long-term memory layer via `LLM Wiki`
- one operational discovery pipeline on `353`
- clear handoffs from discovery -> intelligence -> planning -> conversation -> validation

## Active Profile Map

- `353` -> `Discovery Agent`
- `345` -> `Brand Intelligence Agent`
- `346` -> `Outreach Planning Agent`
- `337` -> `Conversation Agent`
- `333` -> `Feedback / Validation Agent`

The canonical machine-readable registry lives in [registry.yaml](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/registry.yaml).

## Core Rule

Default execution rule:

- `one active browser agent = one dedicated AdsPower profile`

Why:

- shared tabs in one profile corrupt focus and state
- long-running Instagram scans are especially sensitive to tab contention
- isolated profiles make resume and recovery practical

## Agent Responsibilities

### Discovery Agent

- module: `automation/modules/instagram_brand_search/`
- profile: `353`
- responsibility:
  - scan Instagram posts, reels, mentions and following
  - extract brand handles, bios, links, contacts and context
  - produce raw evidence for downstream agents

### Brand Intelligence Agent

- module: `automation/modules/brand_intelligence/`
- profile: `345`
- responsibility:
  - web / reviews / social scan
  - evaluate reputation, frequency of mentions, tone, niche, geo, price segment, blogger fit
  - produce dossier and score

### Outreach Planning Agent

- module: `automation/modules/outreach_planning/`
- profile: `346`
- responsibility:
  - decide whether to contact at all
  - choose channel: Telegram, email, Instagram DM
  - produce personalized angle and outreach plan

### Conversation Agent

- module: `automation/modules/conversation/`
- profile: `337`
- responsibility:
  - run approved conversations
  - obey rate limits, policy rules, and memory of prior threads
  - default mode: human approval required

### Feedback / Validation Agent

- module: `automation/modules/feedback_validation/`
- profile: `333`
- responsibility:
  - inspect deeper complaints and review evidence
  - validate or challenge claims
  - prepare deeper follow-up tasks
  - no automatic contact with reviewers/commenters without explicit approval

## Runtime Layers

### 1. Provider Layer

- `automation/adspower.py`
- future optional providers can be added here

Responsibilities:

- start and stop profile
- profile lookup
- attach over CDP

### 2. Browser Layer

- `automation/browser.py`
- `automation/human.py`

Responsibilities:

- Playwright attach
- screenshots
- page stability and humanized actions

### 3. Role Modules

- `automation/modules/instagram_brand_search/`
- `automation/modules/brand_intelligence/`
- `automation/modules/outreach_planning/`
- `automation/modules/conversation/`
- `automation/modules/feedback_validation/`
- `automation/modules/subagents/`

Responsibilities:

- role-specific state
- role-specific policies
- outputs and status files

### 4. Shared Memory Layer

- `knowledge/llm_wiki/`

Responsibilities:

- store compiled knowledge pages about brands, bloggers, contacts, campaigns, conversations and decisions
- provide shared working memory for all agents
- remain human-readable and editable

Important:

- this is not RAG
- this layer is summary memory and structured knowledge
- raw evidence stays in source artifacts and markdown outputs

### 5. Orchestration Layer

Current orchestration:

- `Discovery Agent` is the production runner
- `subagents` module is the browser-bound control plane for the other roles

Target orchestration:

1. discovery writes evidence
2. intelligence enriches and scores
3. outreach planning decides channel and angle
4. conversation runs only with approval gate
5. feedback agent deep-validates when risk or ambiguity is high

## State Model

Each agent should own:

- one state file
- one output directory
- one artifact directory
- one memory workspace under `knowledge/llm_wiki`

Resume priority for browser agents:

1. current entity being processed
2. current page / URL
3. last completed action
4. role-specific completed items

## LLM Wiki

The LLM Wiki architecture is documented in [llm_wiki.md](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/llm_wiki.md).

## Legacy Archive

The old `genaipro / genai` workflow is archived in:

- [archive/genaipro_legacy](/c:/Users/occult/Desktop/auto/autoskill/archive/genaipro_legacy)
