# Scripts

Top-level entrypoints are intentionally limited to the main operational commands:

- `run_supervisor.py`
- `run_instagram_brand_search.py`
- `run_company_enrichment.py`
- `run_theblueprint_career_parser.py`
- `build_theblueprint_people_targets.py`
- `build_theblueprint_master_report.py`

Secondary scripts are grouped by purpose:

- `scripts/admin/` for maintenance, rebuilds, queue operations, and repair helpers
- `scripts/reporting/` for audits and derived reports
- `scripts/outreach/` for delivery scripts and channel-specific send flows
- `scripts/experiments/` for one-off evaluators and probes
