# Agent Architecture

## Goal

Unify all browser automations under one runtime so each workflow behaves like a separate job module, while still reusing:

- profile startup and attachment
- humanized browser actions
- state persistence
- artifacts and logs
- retry and recovery logic

## Execution Model

Each automation job should map to one logical agent:

- `genaipro_reference_agent`
- `instagram_brand_search_agent`

Each agent owns:

- one provider binding: `AdsPower` / later `Octo`
- one browser profile
- one job config
- one state file
- one artifact directory

## Concurrency Rule

Default rule:

- `one active agent = one browser profile`

Recommended parallel mode:

- `genaipro` on profile `A`
- `instagram_brand_search` on profile `B`
- for your current setup, keep `instagram_brand_search` on `353` and run `genaipro` on another profile when parallelizing

Possible but not recommended:

- two agents in different tabs of the same profile

Why this is risky:

- shared keyboard and page focus
- shared downloads
- shared cookies and rate limits
- harder state recovery after interruptions
- easier to corrupt current position in long-running Instagram scans

Use same-profile parallel tabs only for read-mostly tasks and only after the single-agent flows are stable.

Practical recommendation for your repo:

- do not run `genaipro` and `instagram_brand_search` at the same time on `353`
- if you want true sub-agent style parallelism, bind each module to its own AdsPower profile

## Runtime Layers

### 1. Provider Layer

- `automation/adspower.py`
- later optional `automation/octo.py`

Responsibilities:

- start/stop profile
- rotate proxy if needed
- attach over CDP

### 2. Browser Layer

- `automation/browser.py`
- `automation/human.py`

Responsibilities:

- Playwright connect
- screenshots
- scroll/click/type helpers
- page stability checks

### 3. Module Layer

One folder per workflow family:

- `automation/modules/genai/`
- `automation/modules/instagram_brand_search/`

Responsibilities:

- site-specific navigation
- selectors
- checkpoint semantics
- candidate extraction logic

### 4. Job Layer

YAML config per run type:

- `automation/modules/genai/job.yaml`
- `automation/modules/instagram_brand_search/job.yaml`

Responsibilities:

- profile binding
- input files
- output locations
- policy knobs

### 5. Runner Layer

- `scripts/run_genaipro_reference_batch.py`
- `scripts/run_instagram_brand_search.py`

Responsibilities:

- load config
- instantiate runtime
- start module workflow
- write logs and artifacts

## Instagram Module Design Intent

Instagram brand search should be resumable by post permalink, not by scroll offset.

Checkpoint priority:

1. current blogger profile URL
2. current post/reel permalink
3. last processed shortcode
4. per-blogger processed candidate handles

That makes recovery practical even when Instagram reorders loaded content or only loads posts in batches.
