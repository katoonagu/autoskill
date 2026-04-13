from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.mail_outreach import build_contact_registry, send_mailru_message, write_mail_outreach_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test email through Mail.ru profile 337.")
    parser.add_argument("--to", dest="to_email", required=True, help="Recipient email")
    parser.add_argument("--subject", default="test", help="Email subject")
    parser.add_argument("--body", default="test", help="Email body")
    args = parser.parse_args()

    result = asyncio.run(
        send_mailru_message(
            PROJECT_ROOT,
            to_email=args.to_email,
            subject=args.subject,
            body=args.body,
        )
    )
    registry = build_contact_registry(PROJECT_ROOT)
    write_mail_outreach_outputs(PROJECT_ROOT, registry, [])
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
