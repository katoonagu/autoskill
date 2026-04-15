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
from automation.modules.brand_arbiter.worker import _heuristic_packet


VARIANTS = {
    "conservative": {"readiness_threshold": 70, "risk_threshold": 50},
    "balanced": {"readiness_threshold": 64, "risk_threshold": 60},
    "aggressive": {"readiness_threshold": 58, "risk_threshold": 68},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate offline brain variants on saved evidence bundles.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of evidence bundles to evaluate.")
    return parser.parse_args()


def evaluate_variant(packet: dict, *, readiness_threshold: int, risk_threshold: int) -> str:
    if packet["risk_score"] >= risk_threshold or packet["need_more_research"]:
        return "validate"
    if packet["outreach_readiness_score"] >= readiness_threshold:
        return "plan_outreach"
    return "hold"


def main() -> None:
    args = parse_args()
    evidence_paths = sorted((PROJECT_ROOT / "artifacts" / "brand_intelligence").glob("*/evidence_bundle.json"))[: args.limit]
    rows = []
    dummy_task = AgentTask(task_id="offline_eval", task_type="brand_arbiter.evaluate_case", assigned_agent="brand_arbiter_agent")
    for evidence_path in evidence_paths:
        evidence_bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        packet = _heuristic_packet(dummy_task, evidence_bundle, media_report=None)
        verdicts = {name: evaluate_variant(packet, **config) for name, config in VARIANTS.items()}
        rows.append(
            {
                "brand_handle": evidence_bundle.get("brand_handle"),
                "base_confidence": packet["confidence"],
                "base_risk_score": packet["risk_score"],
                "base_outreach_readiness_score": packet["outreach_readiness_score"],
                "variant_verdicts": verdicts,
            }
        )

    output_dir = PROJECT_ROOT / "artifacts" / "offline_eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "brain_variants_summary.json"
    md_path = output_dir / "brain_variants_summary.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = ["# Brain Variant Evaluation", ""]
    for row in rows:
        md_lines.append(f"## @{row['brand_handle']}")
        md_lines.append(f"- confidence: {row['base_confidence']}")
        md_lines.append(f"- risk_score: {row['base_risk_score']}")
        md_lines.append(f"- outreach_readiness_score: {row['base_outreach_readiness_score']}")
        for variant_name, verdict in row["variant_verdicts"].items():
            md_lines.append(f"- {variant_name}: {verdict}")
        md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8-sig")
    print(json.dumps({"cases": len(rows), "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()


