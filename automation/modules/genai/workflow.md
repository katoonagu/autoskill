# Genaipro Reference Workflow

## Goal

Use AdsPower profile `353` to process every image from the local `reference/` folder through the Genaipro web app, one by one, with a fixed prompt and fixed generation settings.

The flow must:

- open a usable account on `https://genaipro.vn/veo-account-selection`
- prefer `Ultra tier`, otherwise use `Pro`
- skip accounts where `users` are present
- switch to another account if the current one loads too long or fails to open
- click `Select and access`
- create and open a `New project`
- verify generation settings before each run
- upload one reference image
- open the uploaded image in its own working view
- paste the prompt from `prompts_for_reference/promt_for_reference.md`
- send the generation from that image view
- wait for the result
- download `2K`
- move the processed reference file into `reference_done/`
- navigate back to the project workspace
- continue with the next file

## Fixed Inputs

- AdsPower profile: `353`
- site: `https://genaipro.vn/veo-account-selection`
- prompt file:
  [promt_for_reference.md](C:\Users\User\OneDrive\Desktop\tesett\prompts_for_reference\promt_for_reference.md)
- reference input dir:
  [reference](C:\Users\User\OneDrive\Desktop\tesett\reference)
- processed reference dir:
  [reference_done](C:\Users\User\OneDrive\Desktop\tesett\reference_done)
- download dir:
  [output\genaipro_4k](C:\Users\User\OneDrive\Desktop\tesett\output\genaipro_4k)

## UI Requirements

Before each generation, the script must verify:

- image mode is selected, not video
- aspect ratio is `9:16`
- image count is `x1`
- lower model bar shows `Nano Banana Pro`

Fallback:

- if `Nano Banana Pro` is not available but `Nano Banana 2` is present, log it explicitly and continue only if this fallback is intentionally allowed for that run

## Account Selection Rules

### Preferred account

Pick:

- any `Ultra tier` account first
- if no valid Ultra exists, pick `Pro`

### Reject account if

- row shows `users`
- account never fully opens
- `Select and access` does not lead to a working project page
- project page loads but generator UI does not become interactive within the timeout

### Fallback

If the chosen account fails:

1. go back to account selection
2. choose another valid account
3. repeat until success or max attempts

## Project Flow

1. Close the extension popup because it is already installed.
2. Enter a valid account.
3. Click `Select and access`.
4. Click `New project`.
5. Open the new project if it is not already active.

## State Persistence And Recovery

The runner must remember:

- selected account email
- selected account tier
- account row identifier if available
- project identifier
- project title if visible
- project URL if available
- current reference filename in progress
- successfully completed reference filenames

Persist this state to a local JSON file between steps.

### Recovery behavior

If the browser later lands on the account list or home screen again:

1. load the saved state
2. try to re-enter the same saved account first
3. once inside Flow, try to reopen the same saved project
4. only create a new project if the saved one cannot be found

If the current project already exists and is valid, prefer reopening it instead of creating another one.

### Why this matters

Without state persistence, the runner can:

- switch to a different account mid-batch
- lose the project where uploads were happening
- duplicate projects
- lose track of which reference file was being processed

That is unacceptable for a multi-image queue.

## Per-Image Processing Loop

For each file in `reference/`:

1. Click `+`
2. Click `Upload image`
3. Upload exactly one file
4. Confirm it appears in the project workspace
5. Click the uploaded image to open its working view
6. Read prompt text from `promt_for_reference.md`
7. Paste the prompt into the lower prompt bar inside that image view
8. Confirm:
   - image mode
   - `9:16`
   - `x1`
   - `Nano Banana Pro`
9. Send generation
10. Wait until image result is present and no longer in loading state
11. Download in `2K`
12. Save the file to output directory
13. Move the source image from `reference/` to `reference_done/`
14. Navigate back to the project workspace
15. Reset UI if needed for the next file

## Success Conditions

Per image:

- uploaded reference is visible before send
- uploaded reference opens in a dedicated working view
- generation finishes without visible error
- `2K` download succeeds
- output file exists in output dir
- source file is moved into `reference_done/`
- state file is updated to reflect the completed file

Per run:

- all eligible files from `reference/` are processed exactly once
- failures are logged with screenshot artifacts

## Failure Handling

### Account-level failure

Symptoms:

- page hangs
- inaccessible project
- button clicks do nothing
- generator controls never appear

Action:

- first try restoring the saved account
- if the saved account is unavailable, switch account and update state

### Generation-level failure

Symptoms:

- generation stalls too long
- result does not appear
- download menu missing

Action:

- retry current image once
- if still broken, capture failure screenshot and leave the source file in place
- continue with next image only if that is configured for the run

### Navigation-level failure

Symptoms:

- browser jumps back to home
- project screen disappears
- project picker opens unexpectedly

Action:

- load persisted state
- reopen saved account
- reopen saved project
- resume from the saved current reference file

## Logging Requirements

Log these events:

- selected account tier and identifier
- restored saved account or not
- whether fallback from Ultra to Pro happened
- created new project or reused existing project
- saved project identifier / URL
- each uploaded filename
- prompt insertion success
- actual detected model
- generation start and finish time
- downloaded filename
- moved source filename
- failures and retry reason

## Notes For Runner Implementation

This workflow is a good fit for:

- AdsPower profile start through Local API
- Playwright `connect_over_cdp`
- reusable human interaction helpers
- a deterministic queue runner

Implementation should live as:

- recipe:
  `automation/modules/genai/recipe.py`
- runner:
  `automation/modules/genai/runners/run_reference_batch.py`

## Recording Advice

If selectors are unstable, the fastest way to finish the recipe is:

1. run the flow once manually in AdsPower profile `353`
2. record a short screen video or capture Playwright codegen output
3. use that recording only to lock selectors and exact click order
