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

from automation.modules.mail_outreach import (
    build_contact_registry,
    run_mailru_cycle,
    write_mail_outreach_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sequential Mail.ru outreach batch.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of emails to send")
    args = parser.parse_args()

    registry = build_contact_registry(PROJECT_ROOT)
    cycle = asyncio.run(run_mailru_cycle(PROJECT_ROOT, registry, send_ready=True, limit=args.limit))
    outputs = write_mail_outreach_outputs(PROJECT_ROOT, registry, cycle["audits"])
    print(f"Sent {cycle['sent_count']} emails")
    print(f"artifact_dir: {cycle['artifact_dir']}")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()


