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

from automation.modules.instagram_dm_outreach import build_test_dm_message, send_instagram_dm_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test Instagram DM through AdsPower profile 333.")
    parser.add_argument("--target-url", required=True, help="Instagram profile URL")
    parser.add_argument("--message", default="", help="Override default test message")
    args = parser.parse_args()

    message = args.message.strip() or build_test_dm_message()
    result = asyncio.run(
        send_instagram_dm_message(
            PROJECT_ROOT,
            target_url=args.target_url,
            message=message,
            profile_no="333",
        )
    )
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()


