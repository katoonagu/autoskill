# Browser Subagents

This module is the browser-bound control plane for dedicated AdsPower-backed agents.

## Active Profile Map

- `353` -> `Discovery Agent`
- `345` -> `Brand Intelligence Agent`
- `346` -> `Outreach Planning Agent`
- `337` -> `Conversation Agent`
- `333` -> `Feedback / Validation Agent`

## Roles

- `Discovery Agent`
  - Instagram discovery over posts, reels, mentions and following
  - handled by the existing `instagram_brand_search` module
- `Brand Intelligence Agent`
  - web/reviews/social scan
  - reputation, mention frequency, tone, niche, geo, price segment, blogger fit
- `Outreach Planning Agent`
  - should we write at all
  - which channel to use
  - what personalized outreach angle to use
- `Conversation Agent`
  - handles approved outreach and follow-up
  - human approval stays enabled by default
- `Feedback / Validation Agent`
  - deeper validation of reviews, complaints and external signals
  - no automatic outreach to reviewers/commenters without explicit approval

## Runtime Notes

- one active browser agent = one AdsPower profile
- `Discovery Agent` remains the current Python workflow on `353`
- the probe runner only launches agents whose `enabled: true` is set in `job.yaml`

## Output

- state: `automation/state/subagents/<agent>.json`
- status: `output/subagents/<agent>/status.md`
- screenshot: `output/subagents/<agent>/landing.png`
- per-run log: `output/playwright/<timestamp>_subagent_<agent>/run.log`
