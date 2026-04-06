# Automation Plan

Date: `2026-04-05`

## Idea Summary

Build a browser automation stack for creator-manager workflows where the agent can:

- reuse an already logged-in browser profile
- open specific websites and app flows
- upload local files
- edit fields, click buttons, and run workflows
- download outputs back to local folders
- later scale this into brand research, lead qualification, and outreach preparation

The key requirement is to avoid re-login on every run and to keep browser state stable across sessions.

## Main Use Cases From History

### 1. Creative Tool Automation

- open a generation app such as Higgsfield
- insert prompts
- upload references
- run generations
- pick the best result
- download it to a local folder

### 2. Workflow App Automation

- open a flow app such as Weavy
- load a prepared workflow
- upload a local brand reference image to the input node
- optionally adjust a few known node fields
- run the workflow
- collect the output

### 3. Research Automation

- collect brands from СНГ market sources
- find public contacts
- assess creator-readiness
- analyze reputation
- identify hero products
- build outreach-ready dossiers

## Core Architecture

### Option A: Browser Profile Host + Playwright

This is the best long-term option.

- profile host:
  `Octo Browser` or `AdsPower`
- browser profile stores:
  cookies, localStorage, auth state, proxy, browser fingerprint settings
- local or remote orchestrator starts the profile through its API
- `Playwright` attaches to that running profile through `CDP`
- automation then runs inside the already logged-in browser

Result:

- no repeated manual sign-in
- reusable session state
- one consistent profile per platform or use case

### Option B: Firecrawl Session + Playwright-Style Control

Useful for temporary browser tasks or already existing Firecrawl sessions.

- Firecrawl keeps the browser session
- quick actions happen through `agent-browser`
- precise actions happen through Playwright-style `page` calls in the same session

Result:

- fast to start
- useful for one-off tasks
- weaker as a permanent personal browser-profile system than Octo or AdsPower

## Recommended Stack

### Base Layer

- `Playwright` for actual browser control
- `Octo Browser` as preferred persistent profile host
- `AdsPower` as alternative if its API or MCP is more convenient for your setup

### Thin Wrapper Layer

Create a small local service or script that exposes simple actions:

- `start_profile(profile_name)`
- `connect_browser(profile_name)`
- `open_url(url)`
- `upload_file(selector, path)`
- `fill_field(selector, text)`
- `click(selector)`
- `download_latest(target_dir)`

This wrapper should hide profile API details and CDP attachment logic.

### Optional MCP Layer

If the browser host has MCP:

- use MCP as the control layer

If it does not:

- MCP is not required
- a local wrapper around the browser host API is enough

## Why Playwright

`Playwright` is the correct execution layer because it can:

- attach to an existing browser via `CDP`
- upload local files reliably
- wait for selectors and network states
- capture downloads
- handle dialogs, frames, and dynamic apps
- run autonomously without using the physical mouse

Important:

- Playwright does not use your real mouse hand
- it sends browser events programmatically
- it can run in a separate browser or remote session without interrupting your local work

## Human-Like Behavior Plan

This is for stability and realistic UI interaction, not for bypassing site safeguards.

### Level 1: Basic Natural Motion

Implement these first:

- smooth mouse movement using `page.mouse.move(x, y, { steps })`
- short randomized pauses between actions
- tiny delays before clicking after hover
- scroll before interacting with off-screen elements
- avoid instant multi-action bursts

### Level 2: Reusable Interaction Helpers

Create helper functions:

- `humanMoveTo(locator)`
- `humanClick(locator)`
- `humanType(locator, text)`
- `humanScrollIntoView(locator)`

These helpers should:

- resolve element box coordinates
- move in several steps
- add slight timing jitter
- click only after visibility and stability checks

### Level 3: Visual Stability Checks

Before critical interactions:

- confirm element is visible
- confirm element is enabled
- confirm layout is stable
- confirm no overlay blocks the element

This matters more than fake “humanity”.

## About Plugins And Extensions

### Good Uses

- helper libraries for smoother cursor movement
- file-picker handling helpers
- app-specific selector maps
- retry and wait utilities
- logging, screenshots, and download tracking

### Avoid

- opaque “stealth” stacks used to bypass platform restrictions
- random anti-detection bundles you do not control
- over-randomized behavior that reduces reliability

The safest design is:

- explicit Playwright code
- your own helper functions
- deterministic selectors wherever possible

## Practical Execution Model

### Mode 1: Mapping Run

First run on a new site:

- inspect the UI
- identify stable selectors
- document the action order
- save a site-specific automation recipe

### Mode 2: Deterministic Run

Later runs:

- start the saved profile
- attach Playwright
- load the site
- execute the known recipe
- save outputs and logs

This is how the system becomes cheap in tokens and stable in behavior.

## Site-Specific Notes

### Instagram

- use a logged-in browser profile
- public scraping is unreliable because of login walls
- browser automation is fine for reading visible account data inside an authenticated session

### Higgsfield

- best fit for prompt insertion, generation, and result download
- can work well with an authenticated profile and Playwright download capture

### Weavy

- good candidate if the flow is already built
- reliable for uploading references and editing known fields
- less reliable for free-form graph editing on the canvas

## Recommended Development Order

1. Set up one persistent browser profile host.
2. Build a minimal Playwright wrapper that attaches over `CDP`.
3. Implement shared helpers for:
   file upload, click, type, wait, screenshot, download.
4. Add human-like cursor and timing helpers.
5. Build one site recipe end-to-end.
6. Add structured local logging and output folders.
7. Expand to more sites only after the first workflow is stable.

## Suggested First Milestone

Implement one full browser recipe:

- open a logged-in profile
- go to a known app page
- upload one local file
- fill one prompt
- click run
- wait for completion
- download the result to a local folder

If this works cleanly, the rest of the system is straightforward.

## Project Direction

Long-term, the system should become:

- `profile host` + `Playwright runner` + `site recipes` + `research/output pipeline`

That gives you:

- reusable auth state
- local file access
- deterministic web automation
- lower token usage than repeated DOM interpretation
- a clean path toward large-scale manager workflows
