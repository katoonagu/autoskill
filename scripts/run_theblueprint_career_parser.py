"""Parse The Blueprint career archive into a reviewable YAML export.

Usage:
    python scripts/run_theblueprint_career_parser.py
    python scripts/run_theblueprint_career_parser.py --mode seed-pages --page-id 39253 --page-id 39231
    python scripts/run_theblueprint_career_parser.py --mode brand-pages --brand-slug tbank --brand-slug befree
    python scripts/run_theblueprint_career_parser.py --mode brand-pages --brand-limit 50 --max-workers 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.sources.theblueprint_career import (
    DEFAULT_BLUEPRINT_PAGE_IDS,
    build_blueprint_brand_export,
    build_blueprint_career_export,
    write_blueprint_career_export,
)
from automation.modules.company_contacts_enrichment.theblueprint_shortlist import (
    build_theblueprint_shortlist_payload,
    load_yaml_payload,
    write_theblueprint_shortlist,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse The Blueprint career archive")
    parser.add_argument(
        "--mode",
        choices=["brand-pages", "seed-pages"],
        default="brand-pages",
        help="brand-pages crawls all employers from the left-column directory; seed-pages uses explicit article ids.",
    )
    parser.add_argument(
        "--page-id",
        type=int,
        action="append",
        dest="page_ids",
        help="Specific The Blueprint career page id to parse. Repeat the flag for multiple pages.",
    )
    parser.add_argument("--limit", type=int, help="Parse only the first N default seed page ids")
    parser.add_argument(
        "--brand-slug",
        action="append",
        dest="brand_slugs",
        help="Specific employer slug(s) from /career/brand/<slug>.",
    )
    parser.add_argument("--brand-limit", type=int, help="Crawl only the first N employer pages from the career directory")
    parser.add_argument("--max-workers", type=int, default=8, help="Concurrent fetch workers for brand page crawling")
    parser.add_argument("--output-file", type=str, help="Where to write the YAML export")
    parser.add_argument(
        "--refresh-shortlist",
        action="store_true",
        help="After writing archive output, rebuild inputs/theblueprint_career_hiring.yaml from it.",
    )
    parser.add_argument(
        "--shortlist-output-file",
        type=str,
        default="inputs/theblueprint_career_hiring.yaml",
        help="Where to write the reduced shortlist YAML when --refresh-shortlist is used.",
    )
    args = parser.parse_args()

    if args.mode == "seed-pages":
        page_ids = list(args.page_ids or DEFAULT_BLUEPRINT_PAGE_IDS)
        if args.limit:
            page_ids = page_ids[: max(args.limit, 0)]
        payload = build_blueprint_career_export(page_ids)
        output_file = args.output_file or "output/company_contacts_enrichment/theblueprint_career_seed_pages.yaml"
        summary = [
            f"Parsed seed pages: {len(page_ids)}",
            f"Listings: {payload['listing_count']}",
            f"Companies: {payload['company_count']}",
            f"Errors: {len(payload['errors'])}",
        ]
    else:
        payload = build_blueprint_brand_export(
            brand_slugs=list(args.brand_slugs or []),
            brand_limit=args.brand_limit,
            max_workers=max(args.max_workers, 1),
        )
        output_file = args.output_file or "output/company_contacts_enrichment/theblueprint_career_brand_archive.yaml"
        summary = [
            f"Brand catalog count: {payload['brand_catalog_count']}",
            f"Brands crawled: {payload['brands_crawled_count']}",
            f"Article pages: {payload['article_page_count']}",
            f"Listings: {payload['listing_count']}",
            f"Companies: {payload['company_count']}",
            f"Errors: {len(payload['errors'])}",
        ]

    output_path = PROJECT_ROOT / output_file
    write_blueprint_career_export(output_path, payload)

    for line in summary:
        print(line)
    print(f"Output: {output_path}")

    if args.refresh_shortlist:
        existing_payload = load_yaml_payload(PROJECT_ROOT / args.shortlist_output_file)
        shortlist_payload = build_theblueprint_shortlist_payload(
            payload,
            existing_payload=existing_payload,
        )
        shortlist_output_path = PROJECT_ROOT / args.shortlist_output_file
        write_theblueprint_shortlist(shortlist_output_path, shortlist_payload)
        shortlist_summary = shortlist_payload.get("summary") or {}
        print(f"Shortlist companies: {shortlist_summary.get('selected_company_count', 0)}")
        print(f"Shortlist output: {shortlist_output_path}")


if __name__ == "__main__":
    main()
