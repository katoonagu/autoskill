from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.visualization.api import create_agent_canvas_app


def main() -> None:
    app = create_agent_canvas_app(PROJECT_ROOT)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
