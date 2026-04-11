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
