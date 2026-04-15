"""Entry point for company contacts enrichment pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.company_contacts_enrichment.models import EnrichmentTask
from automation.modules.company_contacts_enrichment.state import CompanyEnrichmentState
from automation.modules.company_contacts_enrichment.text_utils import configure_utf8_console, load_yaml_utf8
from automation.modules.company_contacts_enrichment.worker import enrich_company
from automation.paths import artifacts_root, runtime_state_root


def _load_target_companies(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Target companies file not found: {path}")
    data = load_yaml_utf8(path)
    companies: list[dict] = []
    for item in list(data.get("companies") or []):
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized["entity_type"] = str(item.get("entity_type") or "prospect")
        companies.append(normalized)
    return companies


def _matches_company_query(company: dict, needle: str) -> bool:
    haystacks = [str(company.get("name") or "")]
    haystacks.extend(str(alias or "") for alias in company.get("aliases") or [])
    needle_cf = needle.casefold()
    return any(needle_cf in value.casefold() for value in haystacks if value)


def main() -> None:
    configure_utf8_console()

    parser = argparse.ArgumentParser(description="Company Contacts Enrichment Pipeline")
    parser.add_argument("--company", type=str, help="Enrich single company by name")
    parser.add_argument("--priority", type=str, choices=["high", "medium", "low"], help="Filter by priority")
    parser.add_argument("--step", type=int, help="Run only specific step (1-6)")
    parser.add_argument("--no-firecrawl", action="store_true", help="Disable Firecrawl, use free fetchers only")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    parser.add_argument(
        "--include-channels",
        action="store_true",
        help="Include channel/partner entities from mixed research files",
    )
    parser.add_argument(
        "--min-nsx-fit",
        type=int,
        choices=[0, 1, 2, 3],
        help="Only process entries with nsx_fit >= N when the input file provides that field",
    )
    parser.add_argument(
        "--skip-completed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip already enriched companies",
    )
    parser.add_argument("--input-file", type=str, default="inputs/target_companies.yaml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    input_path = PROJECT_ROOT / args.input_file
    companies = _load_target_companies(input_path)
    logging.info("Loaded %d companies from %s", len(companies), input_path)

    if args.company:
        companies = [c for c in companies if _matches_company_query(c, args.company)]
        if not companies:
            logging.error("Company '%s' not found in target list", args.company)
            sys.exit(1)

    if args.priority:
        companies = [c for c in companies if c.get("priority") == args.priority]

    if not args.include_channels:
        before = len(companies)
        companies = [c for c in companies if c.get("entity_type") != "channel"]
        skipped_channels = before - len(companies)
        if skipped_channels:
            logging.info("Skipping %d channel entities", skipped_channels)

    if args.min_nsx_fit is not None:
        before = len(companies)
        companies = [c for c in companies if ("nsx_fit" not in c) or int(c.get("nsx_fit") or 0) >= args.min_nsx_fit]
        filtered = before - len(companies)
        if filtered:
            logging.info("Filtered out %d companies below nsx_fit=%d", filtered, args.min_nsx_fit)

    before = len(companies)
    companies = [c for c in companies if int(c.get("nsx_fit") or 1) > 0]
    skipped_non_targets = before - len(companies)
    if skipped_non_targets:
        logging.info("Skipping %d non-target entries with nsx_fit=0", skipped_non_targets)

    state_path = runtime_state_root(PROJECT_ROOT) / "company_enrichment_state.json"
    state = CompanyEnrichmentState.load(state_path)

    if args.skip_completed:
        before = len(companies)
        companies = [
            c
            for c in companies
            if not state.is_completed(
                "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(c.get("name") or "").strip().lower())
            )
        ]
        skipped = before - len(companies)
        if skipped:
            logging.info("Skipping %d already completed companies", skipped)

    if args.dry_run:
        print(f"\n{'=' * 60}")
        print(f"DRY RUN: {len(companies)} companies to enrich")
        print(f"Firecrawl: {'disabled' if args.no_firecrawl else 'enabled'}")
        print(f"Steps: {[args.step] if args.step else [1, 2, 3, 4, 5, 6]}")
        print(f"{'=' * 60}\n")
        for index, company in enumerate(companies, 1):
            name = company.get("name", "?")
            priority = company.get("priority", "?")
            sector = company.get("sector", "?")
            entity_type = company.get("entity_type", "prospect")
            nsx_fit = company.get("nsx_fit", "-")
            print(f"  {index:3d}. [{priority:6s}] [{entity_type:8s}] [fit={nsx_fit}] {name:30s} ({sector})")
        print()
        return

    use_firecrawl = not args.no_firecrawl
    steps = [args.step] if args.step else [1, 2, 3, 4, 5, 6]

    total = len(companies)
    success = 0
    failed = 0

    for index, company_data in enumerate(companies, 1):
        name = str(company_data.get("name") or "")
        aliases = list(company_data.get("aliases") or [])
        sector = str(company_data.get("sector") or "")
        priority = str(company_data.get("priority") or "medium")
        note = str(company_data.get("note") or "")

        task = EnrichmentTask(
            company_name=name,
            aliases=aliases,
            sector=sector,
            priority=priority,
            note=note,
            steps_to_run=steps,
        )

        logging.info("=" * 60)
        logging.info("[%d/%d] Enriching: %s (%s, %s)", index, total, name, sector, priority)
        logging.info("=" * 60)

        try:
            card = enrich_company(PROJECT_ROOT, task, use_firecrawl=use_firecrawl)
            success += 1
            logging.info(
                "Result: %d emails, %d phones, %d decision-makers, confidence=%.0f%%",
                len(card.all_emails),
                len(card.phones),
                len(card.decision_makers),
                card.confidence * 100,
            )
        except Exception as exc:
            failed += 1
            logging.error("FAILED: %s -- %s", name, exc)

    print(f"\n{'=' * 60}")
    print(f"DONE: {success}/{total} succeeded, {failed} failed")
    print(f"Results: {artifacts_root(PROJECT_ROOT) / 'company_contacts_enrichment'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()


