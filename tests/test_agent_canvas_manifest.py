from pathlib import Path

from automation.visualization.manifest_builder import build_agent_canvas_bundle


def test_agent_canvas_bundle_handles_missing_files(tmp_path) -> None:
    (tmp_path / "automation").mkdir()
    (tmp_path / "runtime").mkdir()
    (tmp_path / "artifacts").mkdir()

    bundle = build_agent_canvas_bundle(tmp_path)

    assert bundle["overview"]["id"] == "overview"
    assert sorted(bundle["domains"].keys()) == [
        "browser_runtime",
        "company_contacts_enrichment",
        "control_plane",
        "knowledge_reports",
        "outreach_execution",
    ]
    assert "domain.control_plane" in bundle["nodes"]
    assert bundle["actions"]


def test_agent_canvas_bundle_uses_repo_data() -> None:
    project_root = Path(__file__).resolve().parent.parent

    bundle = build_agent_canvas_bundle(project_root)

    assert bundle["overview"]["nodes"]
    assert bundle["domains"]["company_contacts_enrichment"]["nodes"]
    assert bundle["nodes"]["contacts.master_report"]["detail_markdown"]
