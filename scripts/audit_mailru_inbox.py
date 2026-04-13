from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.mail_outreach import audit_mailru_inbox, build_contact_registry, write_mail_outreach_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Mail.ru inbox for known brand contacts.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum contacts to audit")
    args = parser.parse_args()

    registry = build_contact_registry(PROJECT_ROOT)
    audits = asyncio.run(audit_mailru_inbox(PROJECT_ROOT, registry, limit=args.limit or None))
    outputs = write_mail_outreach_outputs(PROJECT_ROOT, registry, audits)
    print(f"Audited {len(audits)} contacts")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
