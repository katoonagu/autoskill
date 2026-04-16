from __future__ import annotations

from automation.paths import artifacts_root

from ..models import GraphEdge, GraphNode, GraphView
from ..utils import aggregate_status, compact_counts, latest_iso, list_recent_files, make_link, path_mtime_iso


def build_knowledge_view(project_root, *, running_actions: set[str] | None = None) -> GraphView:
    del running_actions
    artifact_root = artifacts_root(project_root)
    wiki_root = project_root / "knowledge" / "llm_wiki"
    supervisor_root = artifact_root / "supervisor"
    contacts_root = artifact_root / "company_contacts_enrichment"

    wiki_md_files = list(wiki_root.rglob("*.md")) if wiki_root.exists() else []
    status_files = []
    for pattern_root in (supervisor_root, contacts_root):
        if pattern_root.exists():
            status_files.extend(pattern_root.glob("*status*.json"))
            status_files.extend(pattern_root.glob("*status*.md"))
    master_reports = []
    for pattern_root in (contacts_root, supervisor_root):
        if pattern_root.exists():
            master_reports.extend(pattern_root.glob("*master_report*.md"))
    recent_wiki = list_recent_files(wiki_root, "**/*.md", limit=5)

    nodes = [
        GraphNode(
            id="domain.knowledge_reports",
            kind="domain",
            status="idle",
            label="Knowledge & Reports",
            subtitle="LLM wiki, status layers, and operator-facing reports.",
            counts=compact_counts(
                {
                    "wiki_docs": len(wiki_md_files),
                    "status_files": len(status_files),
                    "master_reports": len(master_reports),
                }
            ),
            last_updated_at=latest_iso(
                [
                    latest_iso([path_mtime_iso(item) for item in recent_wiki]),
                    latest_iso([path_mtime_iso(item) for item in status_files]),
                    latest_iso([path_mtime_iso(item) for item in master_reports]),
                ]
            ),
            progress_text="Persistent memory and generated reports for operators and agents.",
            links=[
                make_link(project_root, "LLM wiki", wiki_root, kind="directory"),
                make_link(project_root, "Company contacts artifacts", contacts_root, kind="directory"),
            ],
            position={"x": 720, "y": 120},
        ),
        GraphNode(
            id="knowledge.llm_wiki",
            kind="resource",
            status="completed" if wiki_md_files else "idle",
            label="LLM Wiki",
            subtitle="Long-lived structured memory for contacts, evidence, and playbooks.",
            counts=compact_counts({"docs": len(wiki_md_files)}),
            last_updated_at=latest_iso([path_mtime_iso(item) for item in recent_wiki]),
            progress_text="Shared memory layer for agents, playbooks, and contacts.",
            links=[
                make_link(project_root, "Wiki root", wiki_root, kind="directory"),
                make_link(project_root, "Wiki index", wiki_root / "index.md"),
            ],
            position={"x": 160, "y": 240},
            metadata={"recent_items": [item.relative_to(wiki_root).as_posix() for item in recent_wiki]},
        ),
        GraphNode(
            id="knowledge.status_reports",
            kind="resource",
            status="completed" if status_files else "idle",
            label="Status Reports",
            subtitle="JSON/MD snapshots that summarize active system state.",
            counts=compact_counts({"files": len(status_files)}),
            last_updated_at=latest_iso([path_mtime_iso(item) for item in status_files]),
            progress_text="Operational summaries used by the dashboard and operators.",
            links=[
                make_link(project_root, "Supervisor status", supervisor_root / "status_report.json"),
                make_link(project_root, "DM status", artifact_root / "instagram_dm_outreach" / "status_report.json"),
            ],
            position={"x": 520, "y": 240},
        ),
        GraphNode(
            id="knowledge.master_reports",
            kind="resource",
            status="completed" if master_reports else "idle",
            label="Master Reports",
            subtitle="Single-file narrative reports for decision-making.",
            counts=compact_counts({"reports": len(master_reports)}),
            last_updated_at=latest_iso([path_mtime_iso(item) for item in master_reports]),
            progress_text="High-context reports that compress multi-step pipelines.",
            links=[
                make_link(project_root, "Blueprint master report", contacts_root / "theblueprint_master_report.md"),
                make_link(project_root, "Supervisor markdown status", supervisor_root / "status_report.md"),
            ],
            position={"x": 880, "y": 240},
            metadata={"recent_items": [item.name for item in master_reports[:5]]},
        ),
    ]
    edges = [
        GraphEdge(id="kn-1", source="knowledge.llm_wiki", target="knowledge.status_reports"),
        GraphEdge(id="kn-2", source="knowledge.status_reports", target="knowledge.master_reports"),
    ]
    domain_status = aggregate_status([node.status for node in nodes[1:]])
    nodes[0].status = domain_status
    return GraphView(
        id="knowledge_reports",
        label="Knowledge & Reports",
        subtitle="Shared memory, status layers, and long-form reporting.",
        status=domain_status,
        nodes=nodes,
        edges=edges,
        metadata={"domain_id": "knowledge_reports"},
    )
