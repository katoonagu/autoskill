from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.control_plane import SupervisorOptions, run_supervisor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multi-agent control-plane supervisor.")
    parser.add_argument("--max-tasks", type=int, default=25, help="Maximum number of pending tasks to execute in one run.")
    parser.add_argument("--seed-only", action="store_true", help="Only seed tasks from discovery outputs without executing workers.")
    parser.add_argument("--no-seed", action="store_true", help="Do not seed tasks from discovery state before processing.")
    parser.add_argument("--skip-wiki", action="store_true", help="Skip writes into knowledge/llm_wiki during this run.")
    parser.add_argument(
        "--brain-mode",
        choices=("api", "codex", "hybrid"),
        default="",
        help="Override AUTOSKILL_BRAIN_MODE for this run.",
    )
    parser.add_argument(
        "--agents",
        nargs="*",
        default=[],
        help="Optional subset of agent names to execute, for example brand_intelligence_agent outreach_planning_agent.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_supervisor(
        PROJECT_ROOT,
        SupervisorOptions(
            max_tasks=args.max_tasks,
            seed_from_discovery=not args.no_seed,
            seed_only=args.seed_only,
            write_wiki=not args.skip_wiki,
            allowed_agents=tuple(args.agents),
            brain_mode=args.brain_mode,
        ),
    )
    print(summary)


if __name__ == "__main__":
    main()
