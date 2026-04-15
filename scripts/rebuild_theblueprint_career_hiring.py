"""Rebuild the curated The Blueprint hiring shortlist from archive output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.theblueprint_shortlist import (
    build_theblueprint_shortlist_payload,
    load_yaml_payload,
    write_theblueprint_shortlist,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild inputs/theblueprint_career_hiring.yaml from brand archive output")
    parser.add_argument(
        "--archive-file",
        type=str,
        default="output/company_contacts_enrichment/theblueprint_career_brand_archive.yaml",
        help="Archive YAML produced by run_theblueprint_career_parser.py --mode brand-pages",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="inputs/theblueprint_career_hiring.yaml",
        help="Where to write the reduced shortlist YAML",
    )
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=365,
        help="Keep roles published within the last N days",
    )
    args = parser.parse_args()

    archive_path = PROJECT_ROOT / args.archive_file
    output_path = PROJECT_ROOT / args.output_file

    archive_payload = load_yaml_payload(archive_path)
    existing_payload = load_yaml_payload(output_path)
    payload = build_theblueprint_shortlist_payload(
        archive_payload,
        existing_payload=existing_payload,
        freshness_days=max(args.freshness_days, 1),
    )
    write_theblueprint_shortlist(output_path, payload)

    summary = payload.get("summary") or {}
    print(f"Archive companies: {summary.get('archive_company_count', 0)}")
    print(f"Selected companies: {summary.get('selected_company_count', 0)}")
    print(f"Segments: {summary.get('segment_counts', {})}")
    print(f"Excluded: {summary.get('excluded_counts', {})}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
