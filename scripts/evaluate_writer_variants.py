from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


VARIANTS = {
    "concise": {"max_guardrails": 3, "expects_timing_hook": False},
    "balanced": {"max_guardrails": 4, "expects_timing_hook": True},
    "warm": {"max_guardrails": 5, "expects_timing_hook": True},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate offline writer variants on saved outreach planning decisions.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of planning decisions to inspect.")
    return parser.parse_args()


def score_variant(decision: dict, *, max_guardrails: int, expects_timing_hook: bool) -> dict:
    guardrails = list(decision.get("what_not_to_say") or [])
    why_now = str(decision.get("why_now") or "").strip()
    recommended_angle = str(decision.get("recommended_angle") or "").strip()
    score = 0
    if recommended_angle:
        score += 1
    if len(guardrails) <= max_guardrails:
        score += 1
    if expects_timing_hook and why_now:
        score += 1
    elif not expects_timing_hook:
        score += 1
    return {
        "score": score,
        "angle_present": bool(recommended_angle),
        "guardrails_count": len(guardrails),
        "why_now_present": bool(why_now),
    }


def main() -> None:
    args = parse_args()
    decision_paths = sorted((PROJECT_ROOT / "output" / "outreach_planning").glob("*/decision.json"))[: args.limit]
    rows = []
    for decision_path in decision_paths:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        variant_scores = {name: score_variant(decision, **config) for name, config in VARIANTS.items()}
        rows.append(
            {
                "brand_handle": decision.get("brand_handle"),
                "blogger_handle": decision.get("blogger_handle"),
                "variant_scores": variant_scores,
            }
        )

    output_dir = PROJECT_ROOT / "output" / "offline_eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "writer_variants_summary.json"
    md_path = output_dir / "writer_variants_summary.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = ["# Writer Variant Evaluation", ""]
    for row in rows:
        md_lines.append(f"## @{row['brand_handle']} -> @{row['blogger_handle']}")
        for variant_name, result in row["variant_scores"].items():
            md_lines.append(
                f"- {variant_name}: score={result['score']}, angle_present={result['angle_present']}, "
                f"guardrails_count={result['guardrails_count']}, why_now_present={result['why_now_present']}"
            )
        md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8-sig")
    print(json.dumps({"cases": len(rows), "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
