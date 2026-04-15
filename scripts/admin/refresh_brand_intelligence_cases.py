from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane.models import AgentTask
from automation.modules.brand_intelligence.state import BrandIntelligenceState
from automation.modules.brand_intelligence.worker import run_brand_intelligence_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh already collected brand_intelligence evidence bundles."
    )
    parser.add_argument(
        "--handles",
        nargs="*",
        default=[],
        help="Optional specific brand handles to refresh. Defaults to all completed handles from state.",
    )
    parser.add_argument(
        "--write-wiki",
        action="store_true",
        help="Also rewrite knowledge/llm_wiki brand pages during refresh.",
    )
    return parser.parse_args()


def _resolve_snapshot_path(state: BrandIntelligenceState, handle: str) -> Path | None:
    snapshot_path = PROJECT_ROOT / "artifacts" / "supervisor" / "normalized" / "discovery_brand_snapshots" / f"{handle}.json"
    if snapshot_path.exists():
        return snapshot_path

    evidence_info = state.evidence_bundles.get(handle) or {}
    evidence_bundle_path = Path(str(evidence_info.get("evidence_bundle_path") or ""))
    if evidence_bundle_path.exists():
        try:
            payload = json.loads(evidence_bundle_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        candidate = Path(str(payload.get("brand_snapshot_path") or ""))
        if candidate.exists():
            return candidate
    return None


def _refresh_handle(handle: str, *, state: BrandIntelligenceState, write_wiki: bool) -> tuple[bool, str]:
    snapshot_path = _resolve_snapshot_path(state, handle)
    if snapshot_path is None:
        return False, f"{handle}: snapshot not found"

    task = AgentTask(
        task_id=f"refresh_brand_intelligence__{handle}",
        task_type="brand_intelligence.collect_evidence",
        assigned_agent="brand_intelligence_agent",
        source_run_id="manual_refresh",
        entity_refs={"brand_handle": handle},
        inputs={"brand_snapshot_path": str(snapshot_path)},
    )
    run_brand_intelligence_task(PROJECT_ROOT, task, write_wiki=write_wiki)
    return True, f"{handle}: refreshed"


def main() -> None:
    args = parse_args()
    state_path = PROJECT_ROOT / "automation" / "state" / "brand_intelligence_state.json"
    state = BrandIntelligenceState.load(state_path)
    handles = list(args.handles) or list(state.completed_brand_handles)

    refreshed: list[str] = []
    skipped: list[str] = []

    for handle in handles:
        ok, message = _refresh_handle(handle, state=state, write_wiki=args.write_wiki)
        print(message)
        if ok:
            refreshed.append(handle)
        else:
            skipped.append(handle)

    print("")
    print(f"Refreshed: {len(refreshed)}")
    print(f"Skipped: {len(skipped)}")
    if skipped:
        print("Skipped handles:")
        for handle in skipped:
            print(f"- {handle}")


if __name__ == "__main__":
    main()


