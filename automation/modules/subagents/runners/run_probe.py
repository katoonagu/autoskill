from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.subagents.recipe import load_subagent_specs, run_subagent_probe


def load_job_config() -> dict:
    job_path = PROJECT_ROOT / "automation" / "modules" / "subagents" / "job.yaml"
    return yaml.safe_load(job_path.read_text(encoding="utf-8"))


def resolve_project_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def normalize_job_paths(job: dict) -> dict:
    job["state"]["state_dir"] = str(resolve_project_path(job["state"]["state_dir"]))
    for key, raw_path in list(job.get("outputs", {}).items()):
        job["outputs"][key] = str(resolve_project_path(raw_path))
    return job


async def main() -> None:
    job = normalize_job_paths(load_job_config())
    specs = load_subagent_specs(job)
    tasks = [
        run_subagent_probe(PROJECT_ROOT, job, spec, start_delay_sec=index * 2.0)
        for index, spec in enumerate(specs)
    ]
    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
