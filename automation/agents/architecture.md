# Agent Architecture

## Goal

Turn the project into a dedicated task-driven multi-agent operating model with:

- logical agents that own decisions and outputs
- browser backends that are leased only for tasks that actually need them
- one shared long-term memory layer via `LLM Wiki`
- one operational discovery pipeline on `353`
- clear handoffs from discovery -> intelligence -> planning -> conversation -> validation

## Logical Agent Map

- `Discovery Agent`
- `Brand Intelligence Agent`
- `Outreach Planning Agent`
- `Conversation Agent`
- `Feedback / Validation Agent`

## Browser Profile Pool

- `353` -> discovery primary
- `345` -> shared browser research / live validation
- `337` -> conversation primary

The canonical machine-readable registry lives in [registry.yaml](/c:/Users/occult/Desktop/auto/autoskill/automation/agents/registry.yaml).

## Core Rule

Default execution rule:

- `one logical agent != one mandatory browser profile`
- `one browser profile is leased only when the task requires browser access`

Why:

- discovery and conversation truly need stable browser state
- intelligence, planning, and validation can run as task workers without forcing AdsPower usage
- profile leases keep browser contention explicit instead of implicit

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
- task worker implementations for downstream agents

### 4. Control Plane

- `automation/control_plane/`
- `automation/agents/contracts/`
- `runtime/tasks/`
- `runtime/decisions/`

Responsibilities:

- seed tasks from discovery outputs
- dispatch tasks to the right logical agent
- create downstream tasks from routing rules
- create approval records for guarded actions
- manage browser profile leases when tasks need browser access

### 5. Shared Memory Layer

- `knowledge/llm_wiki/`

Responsibilities:

- store compiled knowledge pages about brands, bloggers, contacts, campaigns, conversations and decisions
- provide shared working memory for all agents
- remain human-readable and editable

Important:

- this is not RAG
- this layer is summary memory and structured knowledge
- raw evidence stays in source artifacts and markdown outputs

### 6. Orchestration Layer

Current orchestration:

- `Discovery Agent` is the production runner
- the supervisor seeds tasks from discovery and executes downstream logical workers
- `Brand Intelligence Agent` enriches candidates with live search, fetched page summaries, and traceable `web_research.json` artifacts
- `Conversation Agent` splits into `prepare_draft` and `send_message`, with a second approval gate before the live send
- `subagents` remains a browser probe harness, not the main orchestration mechanism

Target orchestration:

1. discovery writes evidence
2. intelligence enriches and scores
3. outreach planning decides channel and angle
4. conversation runs only with approval gate
5. feedback agent deep-validates when risk or ambiguity is high

## State Model

Control-plane truth now lives in:

- `runtime/tasks/` for task lifecycle
- `runtime/decisions/` for approval lifecycle
- `runtime/state/leases/` for browser profile lease records
- `runtime/state/agents/` for per-agent runtime snapshots

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

