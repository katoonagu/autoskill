from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.mail_outreach import build_contact_registry, write_mail_outreach_outputs


def main() -> None:
    registry = build_contact_registry(PROJECT_ROOT)
    outputs = write_mail_outreach_outputs(PROJECT_ROOT, registry, [])
    print(f"Built contact registry with {len(registry)} contacts")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
