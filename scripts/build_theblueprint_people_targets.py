"""Build stage-2 people targets and report from The Blueprint shortlist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.text_utils import configure_utf8_console
from automation.modules.company_contacts_enrichment.theblueprint_people_targets import (
    build_theblueprint_people_targets_payload,
    load_yaml_payload,
    write_people_targets_report,
    write_people_targets_yaml,
)


def main() -> None:
    configure_utf8_console()
    parser = argparse.ArgumentParser(description="Build outreach-ready people targets from The Blueprint shortlist")
    parser.add_argument(
        "--input-file",
        type=str,
        default="inputs/theblueprint_career_hiring.yaml",
        help="Shortlist YAML produced by rebuild_theblueprint_career_hiring.py",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="artifacts/company_contacts_enrichment/theblueprint_people_targets.yaml",
        help="Where to write the machine-readable people targets YAML",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        default="artifacts/company_contacts_enrichment/theblueprint_people_targets_report.md",
        help="Where to write the human-readable report",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="How many top targets to include",
    )
    args = parser.parse_args()

    shortlist_path = PROJECT_ROOT / args.input_file
    shortlist_payload = load_yaml_payload(shortlist_path)
    payload = build_theblueprint_people_targets_payload(shortlist_payload, top_n=max(args.top_n, 1))

    output_path = PROJECT_ROOT / args.output_file
    report_path = PROJECT_ROOT / args.report_file

    write_people_targets_yaml(output_path, payload)
    write_people_targets_report(report_path, payload)

    summary = payload.get("summary") or {}
    print(f"Shortlist companies scanned: {summary.get('shortlist_company_count', 0)}")
    print(f"Targets built: {summary.get('targets_count', 0)}")
    print(f"Wave counts: {summary.get('wave_counts', {})}")
    print(f"YAML: {output_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()



