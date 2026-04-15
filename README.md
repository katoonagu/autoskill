# Autoskill

`Autoskill` is a local Python project for Instagram brand discovery and downstream outreach workflows.

This is not just a scraper. It is a task-driven multi-agent control plane for the pipeline:

`discovery -> brand intelligence.collect_evidence -> brand_arbiter.evaluate_case -> outreach planning -> conversation -> validation`

## What The Project Does

The main goal of the project is to:

- find brands in Instagram posts, reels, mentions, and following graphs around bloggers
- extract brand entities, handles, bios, links, contact clues, and mention context
- evaluate discovered brands as potential partnership targets
- decide whether outreach should happen at all
- prepare personalized outreach material
- send a message only after explicit approval through a real browser profile
- preserve traceable evidence, operational state, and human-readable memory

The core idea is to separate sourcing, analysis, decision-making, and communication into distinct logical roles instead of collapsing everything into one large agent prompt.

## Technology Model

This is a local agent system where:

- Python is the main runtime
- Instagram discovery runs through AdsPower + Playwright
- downstream logic runs through a task queue and supervisor
- browser profiles are no longer equal to agents one-to-one
- browser access is leased only to tasks that really need it

So the system is designed not as `5 browsers = 5 agents`, but as:

- logical agents
- a control plane
- browser backends
- shared memory
- approval gates

## Core Logical Agents

### 1. Discovery Agent

Role:

- production crawler for Instagram discovery

What it does:

- scans Instagram
- collects raw brand candidates
- extracts handles, bios, links, contact clues, and mention context
- creates source evidence for downstream stages

This is the main source of truth for the initial signal.

### 2. Brand Intelligence Agent

Role:

- evidence collection for a discovered brand

What it does:

- takes a brand candidate from discovery
- runs web research
- looks for official sites, review signals, tone, geo, and price segment
- ranks search results while pushing non-social sources above social pages when possible
- fetches pages and builds summaries
- writes `web_research.json`, `evidence_bundle.json`, and `evidence_report.md`

This is the project's evidence collector, not the final brain.

### 3. Brand Arbiter Agent

Role:

- central reasoning and verdict layer

What it does:

- reads the normalized evidence bundle
- applies structured evaluation in the shape `State -> Criteria -> Analysis -> Verdict`
- writes `intelligence_packet.json` and `arbiter_report.md`
- decides whether the case should go to outreach planning, validation, or optional media enrichment

### 4. Outreach Planning Agent

Role:

- decision layer between intelligence and communication

What it does:

- decides whether to contact at all
- chooses a channel such as Instagram DM, email, or Telegram
- produces a personalized outreach angle
- writes a planning decision instead of sending anything

### 5. Conversation Agent

Role:

- preparation and execution of outbound communication

What it does:

- creates a draft first
- waits for a separate approval before send
- performs the live send only after approval through a leased browser profile
- stores thread state, screenshots, and send status

Important:

- draft generation and send are separated
- send must not happen automatically without explicit approval

### 6. Feedback / Validation Agent

Role:

- risk control and ambiguous-case review

What it does:

- re-checks questionable brands
- looks for complaints, review signals, and contradictions
- can stop a weak or risky case before outreach

## Current Architecture

### Control Plane

The project has a supervisor that:

- seeds tasks from discovery state
- creates task objects
- routes tasks through routing rules
- creates approval records for guarded actions
- promotes approved tasks into execution
- manages browser leases for browser-bound tasks

This is already a control plane, not just a set of ad-hoc scripts.

### Contracts

The system uses formal contracts between stages:

- task types
- routing rules
- approval scopes
- status model
- profile pool

That means handoff between stages should happen through structured tasks instead of loose markdown-only coordination.

### Browser Profiles

The current browser model is:

- `353` = discovery primary
- `345` = shared browser research / validation
- `337` = conversation primary

Important:

- there are more logical agents than mandatory browser profiles
- not every agent needs a dedicated AdsPower profile

## Data Layout

### Operational Truth

Operational truth lives in:

- `runtime/tasks/` for task lifecycle
- `runtime/decisions/` for approval lifecycle
- `runtime/state/leases/` for browser lease records
- `runtime/state/agents/` for runtime snapshots

### Knowledge / Memory

Shared knowledge lives in:

- `knowledge/llm_wiki/`

This is human-readable shared memory for:

- brands
- bloggers
- contacts
- decisions
- conversations
- campaigns

Important:

- this is not RAG
- this is not a vector store
- this is markdown-based shared memory that can be read and edited by a human

### Raw Evidence / Outputs

Raw outputs live in:

- `artifacts/instagram_brand_search/`
- `artifacts/brand_intelligence/`
- `artifacts/conversation/`
- `artifacts/supervisor/`

The principle is:

- raw evidence is separate
- operational state is separate
- summarized knowledge is separate

## End-To-End Flow

The normal scenario is:

1. Discovery finds a brand candidate in Instagram.
2. Supervisor creates a task for Brand Intelligence.
3. Brand Intelligence performs web research and writes a score and dossier.
4. If confidence is low or risk is high, the case goes to Validation.
5. If the brand looks viable, a task is created for Outreach Planning.
6. Outreach Planning decides `contact / hold / validate`.
7. If outreach is selected, an approval is created for `conversation.prepare_draft`.
8. After approval, the draft is created.
9. A separate approval is then created for `conversation.send_message`.
10. Only after the second approval does Conversation Agent send the message through a leased browser profile.
11. After send, the system stores status, screenshots, and conversation state.

## What The Project Is Not

This is not a basic scraper and not a spam bot.

It is designed around:

- traceability
- explicit approvals
- separation of concerns
- browser isolation
- recoverable state
- human-readable memory
- task-driven orchestration

Conceptually, the project is closer to a lightweight agent operating system for outreach workflows than to a single-script automation tool.

## Practical Status

Right now:

- discovery already works as a production-like crawler
- the control plane already exists
- brand intelligence already supports live web research
- conversation is already split into `prepare_draft` and `send_message`
- `send_message` is already integrated with a real browser lease
- validation already exists as a downstream guardrail

So the project is already beyond the "just scripts" stage. Discovery is working, and the broader multi-agent architecture is now represented as a real task system.

## Source Of Truth For Analysis

When analyzing the project, the source of truth should be:

- discovery outputs
- task contracts
- routing rules
- supervisor orchestration
- approvals
- profile pool
- output artifacts
- `llm_wiki` as summarized memory

The project should be interpreted as an agentic control plane for brand discovery, intelligence, planning, and approved outreach.

It should not be interpreted as only a set of Instagram parsing scripts.

## Recommended Agent Split

The best next-step architecture is not "one super-agent that does everything".

The cleaner model is:

- `Discovery Agent`
- `Brain / Intelligence Agent`
- `Offer Writer / Conversation Agent`
- optional `Validation / Deep Research Agent`

### Why Not One Agent For Everything

If one agent researches, evaluates, and writes the offer inside one prompt, several problems appear:

- analysis and persuasion get mixed together
- it becomes harder to debug quality
- the messaging layer starts to inherit noise from raw research
- it becomes difficult to see whether the failure came from research, scoring, or writing

So the better split is:

- one agent is responsible for truth and reasoning
- another agent is responsible for framing and writing

### Recommended Roles

#### Brain / Intelligence Agent

This should be the main reasoning layer.

It should:

- search and evaluate the brand
- decide what evidence matters and what should be ignored
- write the dossier
- produce recommendations
- return `need_more_research` when evidence is weak
- trigger deeper research when a case is ambiguous

Its output should not be only markdown. It should produce a structured intelligence packet.

Suggested fields:

- `brand_score`
- `fit_score`
- `risk_score`
- `confidence`
- `why_this_brand`
- `why_now`
- `what_not_to_say`
- `missing_context`
- `recommended_next_step`
- `offer_inputs`

#### Offer Writer / Conversation Agent

This agent should not re-research the brand from scratch.

It should receive the intelligence packet and:

- write one or more outreach options
- adapt tone to the selected channel
- respect constraints and forbidden claims
- return `need_more_context` if the brain layer did not provide enough material

Key rule:

- the writer should not replace intelligence
- the writer should write from prepared material

#### Validation / Deep Research Agent

This agent should only activate for:

- low-confidence cases
- high-risk cases
- contradictory signals
- cases where stronger personalization is needed

It should not be always-on for every candidate.

## Media And Video Analysis

It makes sense to extend the brain layer with YouTube, Instagram video, and comment analysis, but this should not run for every case by default.

The correct model is selective enrichment.

### Base Layer

The default intelligence layer should use:

- website
- Instagram profile
- links
- reviews
- general web search
- mentions

### Deep Layer

A deeper layer can optionally analyze:

- recent YouTube videos
- recent Instagram reels/posts
- descriptions and captions
- comment patterns
- creator-brand fit
- recurring objections or requests from the audience

This layer should run only when:

- confidence is below threshold
- the brand is promising but unclear
- stronger personalization is needed
- signals conflict with each other

### How To Use Gemini Or Another Vision Model

The correct way to use Gemini here is:

1. scrape video URLs, captions, descriptions, and comments yourself
2. send either the video or carefully selected media inputs to Gemini API
3. ask for a structured report instead of free-form prose

Suggested output schema:

- `video_summary`
- `content_topics`
- `brand_mentions`
- `audience_tone`
- `comment_sentiment`
- `recurring_requests`
- `risk_flags`
- `creator_style`
- `integration_fit`
- `do_not_use_as_signal`

Important:

- comments are weak signals, not truth
- comments should help with tone, objections, and audience patterns
- comments should not be treated as strong evidence of brand quality by themselves

## Recommended Next Evolution

The recommended architecture for the project is:

- keep `Discovery Agent` as the sourcing layer
- make `Brand Intelligence Agent` the main brain
- keep `Outreach Planning Agent` as the decision layer
- make `Conversation Agent` the writer and sender, but only from approved structured inputs
- use `Validation / Deep Research Agent` only for risky or ambiguous cases

The most important rule is:

- one agent should think and evaluate
- another agent should write
- deeper research should be optional and trigger-based

That gives cleaner prompts, clearer responsibilities, better traceability, and less hallucination.

## Main Commands

### Discovery Run

```powershell
python scripts/run_instagram_brand_search.py
```

### Following-Only Run

```powershell
python scripts/run_instagram_following_only.py
```

### Rebuild Discovery Exports From Current State

This command does not open the browser and does not re-scrape Instagram. It rebuilds the discovery outputs from `runtime/state/instagram_brand_search_state.json`.

```powershell
python scripts/rebuild_instagram_brand_exports.py
```

### Sync Organized Brand Tables

This command rebuilds current live exports, keeps the live `brand_links.xlsx`, and refreshes the centralized Excel set in `artifacts/instagram_brand_search/brands/tables/`.

```powershell
python scripts/sync_instagram_brand_tables.py
```

### Subagent Probe Run

```powershell
python scripts/run_subagents_probe.py
```

### Supervisor Run

This is the task-driven control plane entrypoint. It seeds downstream tasks from discovery state, runs logical agents, and promotes approved tasks into browser-backed execution when needed.

```powershell
python scripts/run_supervisor.py --max-tasks 25
```

Brain execution mode can be controlled with `AUTOSKILL_BRAIN_MODE=api|codex|hybrid` or with a one-off CLI override:

```powershell
python scripts/run_supervisor.py --brain-mode codex --max-tasks 25
```

- `api` keeps arbiter execution inside the runtime.
- `codex` moves `brand_arbiter.evaluate_case` tasks into `waiting_codex_review`.
- `hybrid` keeps ordinary arbiter cases in the runtime and routes high-value, weak-evidence, or conflicting cases into Codex review.

### Seed Only

Create structured tasks from discovery outputs without executing downstream workers.

```powershell
python scripts/run_supervisor.py --seed-only
```

### Approval Queue

List pending approvals:

```powershell
python scripts/approve_supervisor_item.py --list
```

Approve one item:

```powershell
python scripts/approve_supervisor_item.py --approval-id <approval-id> --decision approved
```

### Codex Review Queue

List pending manual arbiter cases that were routed into Codex review:

```powershell
python scripts/list_codex_review_queue.py --limit 10
```

Claim a manual review batch:

```powershell
python scripts/claim_codex_review_batch.py --limit 10
```

Finalize one reviewed arbiter task from `codex_reviewing`:

```powershell
python scripts/finalize_codex_review.py --task-id <task-id> --packet-path <packet-json>
```

Refresh the consolidated supervisor dashboard:

```powershell
python scripts/write_status_report.py
```

## Current Discovery Outputs

Main live outputs:

- `artifacts/instagram_brand_search/run_status.md`
- `artifacts/instagram_brand_search/run_status.json`
- `artifacts/instagram_brand_search/brands/brand_links.md`
- `artifacts/instagram_brand_search/brands/brand_dossiers.md`
- `artifacts/instagram_brand_search/brands/blogger_summary.md`
- `artifacts/instagram_brand_search/brands/brand_links.xlsx`

Per-blogger discovery output:

- `artifacts/instagram_brand_search/brands/by_blogger/<handle>/collabs.md`

Following outputs:

- `artifacts/instagram_brand_search/following/<handle>/shortlist.md`
- `artifacts/instagram_brand_search/following/<handle>/brands.md`
- `artifacts/instagram_brand_search/following/following_global.md`
- `artifacts/instagram_brand_search/following/shortlisted_bloggers_for_phase1.md`
- `artifacts/instagram_brand_search/following/shortlisted_bloggers_for_phase1.txt`

## Notes

- `Brand records` in `run_status.md` is the raw count in state.
- `brand_links.xlsx` contains the filtered and deduplicated exportable brands, not the full raw set.
- For a full raw export, see files like `artifacts/instagram_brand_search/brands/brand_records_all_734.xlsx`.
- The control plane stores runtime task JSONs under `runtime/tasks/` and approval JSONs under `runtime/decisions/`.
- Discovery remains the browser-bound production crawler for sourcing brands.
- Brand Intelligence enriches candidates with live web search, non-social result ranking, fetched page summaries, and traceable `web_research.json` reports.
- Conversation has a two-step approval chain: `prepare_draft` and then `send_message`, with the live send path running only through a leased conversation browser profile.

