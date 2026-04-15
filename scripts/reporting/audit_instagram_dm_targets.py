from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_dm_outreach import audit_instagram_dm_targets, write_instagram_dm_status_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Instagram DM targets through AdsPower profile 333.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum targets to audit")
    args = parser.parse_args()

    audits = asyncio.run(audit_instagram_dm_targets(PROJECT_ROOT, limit=args.limit or None))
    report = write_instagram_dm_status_report(PROJECT_ROOT)
    print(f"Audited {len(audits)} Instagram targets")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()


