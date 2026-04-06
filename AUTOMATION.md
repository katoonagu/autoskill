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
- `automation/site_recipes/higgsfield.py`
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

1. Add a new recipe file in `automation/site_recipes/`.
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

- [Genaipro reference workflow](C:\Users\User\OneDrive\Desktop\tesett\automation\site_recipes\genaipro_reference_workflow.md)
- [Genaipro job config](C:\Users\User\OneDrive\Desktop\tesett\automation\jobs\genaipro_reference_job.yaml)
