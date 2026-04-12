# Autoskill

Local automation workspace for Instagram brand discovery and related outreach workflows.

## Main Commands

### Discovery run

```powershell
python scripts/run_instagram_brand_search.py
```

### Following-only run

```powershell
python scripts/run_instagram_following_only.py
```

### Rebuild discovery exports from current state

This command does not open the browser and does not re-scrape Instagram. It rebuilds the discovery outputs from `automation/state/instagram_brand_search_state.json`.

```powershell
python scripts/rebuild_instagram_brand_exports.py
```

### Sync organized brand tables

This command rebuilds current live exports, keeps the live `brand_links.xlsx`, and refreshes the centralized Excel set in `output/instagram_brand_search/brands/tables/`.

```powershell
python scripts/sync_instagram_brand_tables.py
```

### Subagent probe run

```powershell
python scripts/run_subagents_probe.py
```

### Supervisor run

This is the new task-driven control plane. It seeds downstream tasks from discovery state, runs the logical agents, and promotes approved tasks into browser-backed execution when needed.

```powershell
python scripts/run_supervisor.py --max-tasks 25
```

### Seed only

Create structured tasks from discovery outputs without executing downstream workers.

```powershell
python scripts/run_supervisor.py --seed-only
```

### Approval queue

List pending approvals:

```powershell
python scripts/approve_supervisor_item.py --list
```

Approve one item:

```powershell
python scripts/approve_supervisor_item.py --approval-id <approval-id> --decision approved
```

## Current Discovery Outputs

Main live outputs:

- `output/instagram_brand_search/run_status.md`
- `output/instagram_brand_search/run_status.json`
- `output/instagram_brand_search/brands/brand_links.md`
- `output/instagram_brand_search/brands/brand_dossiers.md`
- `output/instagram_brand_search/brands/blogger_summary.md`
- `output/instagram_brand_search/brands/brand_links.xlsx`

Per-blogger discovery output:

- `output/instagram_brand_search/brands/by_blogger/<handle>/collabs.md`

Following outputs:

- `output/instagram_brand_search/following/<handle>/shortlist.md`
- `output/instagram_brand_search/following/<handle>/brands.md`
- `output/instagram_brand_search/following/following_global.md`
- `output/instagram_brand_search/following/shortlisted_bloggers_for_phase1.md`
- `output/instagram_brand_search/following/shortlisted_bloggers_for_phase1.txt`

## Notes

- `Brand records` in `run_status.md` is the raw count in state.
- `brand_links.xlsx` contains the filtered and deduplicated exportable brands, not the full raw set.
- For a full raw export, see files like `output/instagram_brand_search/brands/brand_records_all_734.xlsx`.
- The control plane now stores runtime task JSONs under `automation/tasks/` and approval JSONs under `automation/decisions/`.
- Discovery remains the browser-bound production crawler for sourcing brands.
- Brand Intelligence now enriches candidates with live web search, non-social result ranking, fetched page summaries, and traceable `web_research.json` reports.
- Conversation now has a two-step approval chain: `prepare_draft` and then `send_message`, with the live send path running only through a leased conversation browser profile.
