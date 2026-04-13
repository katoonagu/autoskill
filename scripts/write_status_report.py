from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.reporting import write_reporting_bundle
from automation.control_plane.storage import ensure_control_plane_layout


def main() -> None:
    paths = ensure_control_plane_layout(PROJECT_ROOT)
    print(write_reporting_bundle(paths))


if __name__ == "__main__":
    main()
