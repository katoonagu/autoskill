"""Resolve person-first outreach routes for The Blueprint shortlist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.theblueprint_route_resolver import (
    build_theblueprint_route_resolutions,
    load_yaml_payload,
    write_route_resolutions_report,
    write_route_resolutions_yaml,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Instagram/Telegram/site routes for The Blueprint shortlist")
    parser.add_argument(
        "--input-file",
        type=str,
        default="inputs/theblueprint_career_hiring.yaml",
        help="Shortlist YAML produced by rebuild_theblueprint_career_hiring.py",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="output/company_contacts_enrichment/theblueprint_route_resolutions.yaml",
        help="Where to write the machine-readable resolver output",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        default="output/company_contacts_enrichment/theblueprint_route_resolutions_report.md",
        help="Where to write the human-readable resolver report",
    )
    parser.add_argument("--max-workers", type=int, default=6, help="Parallel workers")
    parser.add_argument(
        "--unresolved-only",
        action="store_true",
        help="Only process entries with weak or placeholder entry routes",
    )
    args = parser.parse_args()

    shortlist_payload = load_yaml_payload(PROJECT_ROOT / args.input_file)
    payload = build_theblueprint_route_resolutions(
        shortlist_payload,
        max_workers=max(args.max_workers, 1),
        unresolved_only=args.unresolved_only,
    )

    output_path = PROJECT_ROOT / args.output_file
    report_path = PROJECT_ROOT / args.report_file
    write_route_resolutions_yaml(output_path, payload)
    write_route_resolutions_report(report_path, payload)

    summary = payload.get("summary") or {}
    print(f"Companies scanned: {summary.get('companies_scanned', 0)}")
    print(f"Resolved person routes: {summary.get('resolved_person_route', 0)}")
    print(f"Resolved brand routes: {summary.get('resolved_brand_route', 0)}")
    print(f"Partial: {summary.get('partial', 0)}")
    print(f"Unresolved: {summary.get('unresolved', 0)}")
    print(f"Errors: {summary.get('error', 0)}")
    print(f"YAML: {output_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
