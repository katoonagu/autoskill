from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.approvals import resolve_approval, write_approval_index
from automation.control_plane.reporting import write_reporting_bundle
from automation.control_plane.storage import ensure_control_plane_layout, list_approvals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List, approve, or reject pending supervisor approvals.")
    parser.add_argument("--list", action="store_true", help="List pending approvals.")
    parser.add_argument("--approval-id", default="", help="Approval id to resolve.")
    parser.add_argument("--decision", choices=["approved", "rejected"], default="approved", help="Resolution to apply.")
    parser.add_argument("--actor", default="human_operator", help="Actor recorded in the approval resolution.")
    parser.add_argument("--notes", default="", help="Optional resolution notes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ensure_control_plane_layout(PROJECT_ROOT)
    if args.list or not args.approval_id:
        pending = [record.to_dict() for _, record in list_approvals(paths, "pending")]
        print({"pending": pending})
        return
    approval = resolve_approval(
        paths,
        approval_id=args.approval_id,
        decision=args.decision,
        actor=args.actor,
        notes=args.notes,
    )
    write_approval_index(paths)
    write_reporting_bundle(paths)
    print(approval.to_dict())


if __name__ == "__main__":
    main()


