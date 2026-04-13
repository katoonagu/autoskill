from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_dm_outreach import build_test_dm_message, run_instagram_dm_cycle, write_instagram_dm_status_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sequential Instagram DM batch through AdsPower profile 333.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of DMs to send")
    parser.add_argument("--message", default="", help="Override default message for this batch")
    args = parser.parse_args()

    cycle = asyncio.run(
        run_instagram_dm_cycle(
            PROJECT_ROOT,
            send_ready=True,
            limit=args.limit,
            message=args.message.strip() or build_test_dm_message(),
        )
    )
    report = write_instagram_dm_status_report(PROJECT_ROOT)
    print(f"Sent {cycle['sent_count']} Instagram DMs")
    print(f"artifact_dir: {cycle['artifact_dir']}")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
