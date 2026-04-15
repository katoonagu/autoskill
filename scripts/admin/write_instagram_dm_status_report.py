from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_dm_outreach import write_instagram_dm_status_report


def main() -> None:
    result = write_instagram_dm_status_report(PROJECT_ROOT)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()


