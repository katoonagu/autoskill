import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_brand_search.recipe import write_markdown_outputs
from automation.modules.instagram_brand_search.state import InstagramBrandSearchState
from automation.paths import resolve_repo_path


def load_job_config() -> dict:
    job_path = PROJECT_ROOT / "automation" / "modules" / "instagram_brand_search" / "job.yaml"
    job = yaml.safe_load(job_path.read_text(encoding="utf-8"))
    job["state"]["state_file"] = str(resolve_repo_path(PROJECT_ROOT, job["state"]["state_file"]))
    for key, raw_path in list(job.get("outputs", {}).items()):
        job["outputs"][key] = str(resolve_repo_path(PROJECT_ROOT, raw_path))
    return job


def main() -> None:
    job = load_job_config()
    state_path = Path(job["state"]["state_file"])
    state = InstagramBrandSearchState.load(state_path)
    write_markdown_outputs(job, state)
    print("Rebuilt Instagram brand exports from current state:")
    print(f"- state: {state_path}")
    print(f"- brand links md: {job['outputs']['discovered_brand_links_md']}")
    print(f"- brand dossiers md: {job['outputs']['extracted_candidates_md']}")
    print(f"- blogger summary md: {job['outputs']['blogger_summary_md']}")
    print(f"- brand links xlsx: {Path(job['outputs']['discovered_brand_links_md']).with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()


