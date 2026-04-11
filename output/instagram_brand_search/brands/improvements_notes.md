# Improvements Notes

## Done

- Removed empty `Followers Count` from the live and common Excel tables.
- Renamed `Sources Count` to `Source Posts Count`.
- Kept `Unique Bloggers Count` as is.

## Checked Files

- `output/instagram_brand_search/brands/brand_links.xlsx`
- `output/instagram_brand_search/brands/tables/brand_links_common.xlsx`
- `output/instagram_brand_search/brands/tables/brand_links_run_01_20260409_211530.xlsx`
- `output/instagram_brand_search/brands/tables/brand_links_run_02_20260410_165749.xlsx`

## Current State

- In `common`: no `Followers Count`, and `Source Posts Count` is present.
- In `run_01` and `run_02`: `Source Posts Count` is also present.

## Suggested Improvements

- Normalize the schema between `run_01` and `run_02`.
- Create `new_brands_from_run_02.xlsx` to show only brands that are new in the second run.
- Create `brands_only_run_01.xlsx` to show brands present in the first run but not in the second.
- Add a contacts layer: `brand_contacts.xlsx` or `creator_contacts.xlsx` with `email`, `telegram`, `phone`, `source profile`, and `confidence`.
- Add a summary workbook such as `brands_dashboard.xlsx` with run counts, new brands, and intersections.
- Keep naming consistent: `brand_links_common`, `brand_links_run_01`, `brand_links_run_02`, `brand_links_current`.

## Most Useful Next Step

1. `brand_links_new_in_run_02.xlsx`
2. `brand_links_only_run_01.xlsx`
3. `brand_contacts.xlsx`

This would create a practical outreach-ready bundle.
