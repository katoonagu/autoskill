from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.visualization import write_agent_canvas_bundle


def main() -> None:
    bundle = write_agent_canvas_bundle(PROJECT_ROOT)
    payload = {
        "generated_at": bundle["generated_at"],
        "domains": sorted(bundle["domains"].keys()),
        "summary": bundle["summary"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
