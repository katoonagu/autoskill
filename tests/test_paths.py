from pathlib import Path

from automation.paths import resolve_repo_path


def test_resolve_repo_path_migrates_runtime_prefixes() -> None:
    project_root = Path("/repo")

    assert resolve_repo_path(project_root, "automation/state/foo.json") == project_root / "runtime/state/foo.json"
    assert resolve_repo_path(project_root, "automation/tasks/inbox/x.json") == project_root / "runtime/tasks/inbox/x.json"
    assert resolve_repo_path(project_root, "automation/decisions/pending/y.json") == project_root / "runtime/decisions/pending/y.json"


def test_resolve_repo_path_migrates_output_prefix() -> None:
    project_root = Path("/repo")

    assert resolve_repo_path(project_root, "output/company_contacts_enrichment/a.yaml") == project_root / "artifacts/company_contacts_enrichment/a.yaml"
    assert resolve_repo_path(project_root, "artifacts/supervisor/status.json") == project_root / "artifacts/supervisor/status.json"
