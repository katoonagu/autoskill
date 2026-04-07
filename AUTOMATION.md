# Browser Automation Runtime

This project now includes a reusable Python runtime for:

- `AdsPower` profile startup
- `Playwright` CDP attachment
- human-like but deterministic interaction helpers
- site-specific recipes

## Files

- `automation/config.py`
- `automation/adspower.py`
- `automation/browser.py`
- `automation/human.py`
- `automation/modules/genai/`
- `automation/modules/instagram_brand_search/`
- `scripts/run_higgsfield_login_fill.py`

## Design Rules

- Use persistent browser profiles instead of recreating auth state.
- Prefer `Playwright` locators and actionability checks over raw sleeps.
- Use `Humanizer` helpers for clicks, typing, and scroll into view.
- Keep per-site logic inside `automation/site_recipes/`.
- Save screenshots and logs under `output/playwright/`.

## Run Example

```powershell
python C:\Users\User\OneDrive\Desktop\tesett\scripts\run_higgsfield_login_fill.py
```

## Extend For Future Scripts

For a new site or workflow:

1. Add a new module or recipe file in the appropriate module folder.
2. Reuse:
   - `AdsPowerSettings`
   - `AdsPowerClient`
   - `connect_profile`
   - `Humanizer`
3. Add a runner script in `scripts/`.

## Recommended Next Recipes

- upload reference image to Weavy input node
- open Higgsfield generation page and insert prompt
- wait for generation completion and download output
- batch process Genaipro references from `reference/` using AdsPower profile `353`

## Existing Job Specs

- [Genaipro reference workflow](C:\Users\User\OneDrive\Desktop\tesett\automation\modules\genai\workflow.md)
- [Genaipro job config](C:\Users\User\OneDrive\Desktop\tesett\automation\modules\genai\job.yaml)
- [Agent architecture](C:\Users\User\OneDrive\Desktop\tesett\automation\agents\architecture.md)
- [Instagram brand search plan](C:\Users\User\OneDrive\Desktop\tesett\automation\modules\instagram_brand_search\plan.md)
- [Instagram brand search job config](C:\Users\User\OneDrive\Desktop\tesett\automation\modules\instagram_brand_search\job.yaml)

## Multi-Agent Direction

Planned runtime model:

- one shared automation runtime
- one module per workflow family
- one runner per job type

Current modules:

- `genaipro_reference`
- `instagram_brand_search` scaffold

Recommended parallel execution:

- one active agent per dedicated browser profile
- separate profiles for `genaipro` and `instagram`

Current Instagram assumptions:

- profile `353`
- scan last `365` days, fallback `112` latest posts/reels
- only explicit `@mentions`
- markdown outputs
- fast humanized pacing
