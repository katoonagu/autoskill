# Instagram Brand Search Plan

## Objective

Automate Instagram sponsorship/brand discovery from prepared blogger profiles.

The bot should:

- open one blogger profile at a time
- inspect posts and reels
- detect likely `@brand` mentions in the blogger's own content
- ignore comments
- open the candidate account
- decide whether it is a real promoted brand or a false positive
- save screenshots and structured output
- return to the exact post and continue

## Inputs

- blogger profile URLs from `inputs/instagram_brand_search/blogger_profiles.txt`
- job settings from `automation/modules/instagram_brand_search/job.yaml`

## Outputs

- screenshots of brand candidates
- markdown report with found brand links and assessments
- per-blogger checkpoints in state JSON
- run log in `artifacts/playwright/...`

## Core Workflow

### Phase 1. Blogger Load

- open blogger profile URL
- verify account page is loaded
- extract handle and profile metadata

### Phase 2. Post Traversal

- open posts/reels sequentially
- work from permalink state, not from raw scroll position
- save `current_post_url` before deep inspection
- primary limit: last `365` days
- fallback limit when time filtering is impractical in UI: last `112` posts/reels

### Phase 3. Mention Detection

Search only in blogger-owned surfaces:

- post caption
- reel/post visible overlay text when accessible
- tagged/mentioned handles visible in the opened post UI

Do not use:

- comments
- commenter handles
- unrelated suggested accounts

### Phase 4. Candidate Validation

For each found `@handle`:

- open profile in a separate tab
- screenshot the account
- inspect bio, profile name, category, link, and content vibe
- decide:
  - real brand
  - store
  - marketplace/reseller
  - unrelated person/page

### Phase 5. Resume

Return to:

- the same blogger
- the same post permalink
- then continue to next post

## Recovery Strategy

### Resume Key

Use post shortcode/permalink as the main checkpoint.

This is better than storing only the scroll offset because Instagram loads content in batches and can change the visible window after refresh.

### Candidate De-duplication

Track:

- processed blogger URLs
- processed post URLs per blogger
- processed brand handles per blogger

## User Decisions Locked In

- browser profile: `AdsPower 353`
- scan depth: `365 days`, fallback `112` latest posts/reels
- only explicit `@mentions`
- write results in `md`
- collect all found Instagram brand profile links into a dedicated markdown file
- use fast humanized pacing to reduce Instagram risk

## Humanized Speed Policy

The crawler should feel active but not bot-like:

- short pauses instead of long idle waits
- small jitter before click/open actions
- slower transitions on post open, profile open, and back-navigation
- no ultra-fast repeated next/close bursts
- no comment expansion or unnecessary hover noise

## Parallelism

Recommended:

- one Instagram agent per dedicated Instagram profile

Not recommended as default:

- multiple Instagram crawlers in different tabs of one same Instagram profile

Reason:

- tab focus and navigation interference
- risk of losing the current post position
- higher chance of rate-limit or account flags

## Remaining Clarifications

1. Stories are currently assumed out of scope for v1. If you want them included later, that should be a separate pass.
2. Brand candidates will be opened in a new tab by default unless you want same-tab navigation.

