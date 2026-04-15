"""Build one consolidated Markdown report for The Blueprint outreach work."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.text_utils import configure_utf8_console
from automation.modules.company_contacts_enrichment.theblueprint_master_report import (
    build_theblueprint_master_report_payload,
    load_yaml_payload,
    write_theblueprint_master_report,
)


def main() -> None:
    configure_utf8_console()
    parser = argparse.ArgumentParser(description="Build a consolidated The Blueprint outreach report")
    parser.add_argument(
        "--shortlist-file",
        type=str,
        default="inputs/theblueprint_career_hiring.yaml",
        help="Reduced shortlist YAML",
    )
    parser.add_argument(
        "--people-targets-file",
        type=str,
        default="artifacts/company_contacts_enrichment/theblueprint_people_targets.yaml",
        help="Stage-2 people targets YAML",
    )
    parser.add_argument(
        "--route-resolutions-file",
        type=str,
        default="artifacts/company_contacts_enrichment/theblueprint_route_resolutions.yaml",
        help="Stage-3 route resolution YAML",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="artifacts/company_contacts_enrichment/theblueprint_master_report.md",
        help="Where to write the consolidated report",
    )
    args = parser.parse_args()

    shortlist_payload = load_yaml_payload(PROJECT_ROOT / args.shortlist_file)
    people_targets_payload = load_yaml_payload(PROJECT_ROOT / args.people_targets_file)
    route_payload = load_yaml_payload(PROJECT_ROOT / args.route_resolutions_file)

    payload = build_theblueprint_master_report_payload(
        shortlist_payload,
        people_targets_payload,
        route_payload,
    )

    output_path = PROJECT_ROOT / args.output_file
    write_theblueprint_master_report(output_path, payload)

    summary = payload.get("summary") or {}
    print(f"Shortlist: {summary.get('shortlist_company_count', 0)}")
    print(f"Top targets: {summary.get('top_targets_count', 0)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()



