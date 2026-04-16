from __future__ import annotations

from pathlib import Path

from ..models import GraphEdge, GraphNode, GraphView, NodeActionRef
from ..utils import (
    aggregate_status,
    compact_counts,
    derive_status,
    latest_iso,
    make_link,
    path_mtime_iso,
    safe_read_text,
    safe_read_yaml,
)


def _yaml_summary(path: Path) -> dict[str, int]:
    payload = safe_read_yaml(path)
    summary = payload.get("summary") or {}
    return {key: int(value or 0) for key, value in summary.items() if isinstance(value, (int, float))}


def _count_listings(path: Path) -> int:
    payload = safe_read_yaml(path)
    if isinstance(payload.get("companies"), list):
        return len(payload["companies"])
    if isinstance(payload.get("resolutions"), list):
        return len(payload["resolutions"])
    if isinstance(payload.get("targets"), list):
        return len(payload["targets"])
    return 0


def _recent_lines_from_md(path: Path, *, limit: int = 5) -> list[str]:
    content = safe_read_text(path)
    lines = [line.strip("- ").strip() for line in content.splitlines() if line.strip().startswith("- ")]
    return lines[:limit]


def build_company_contacts_view(project_root: Path, *, running_actions: set[str] | None = None) -> GraphView:
    running_actions = running_actions or set()
    root = project_root / "artifacts" / "company_contacts_enrichment"
    shortlist_path = project_root / "inputs" / "theblueprint_career_hiring.yaml"
    archive_path = root / "theblueprint_career_brand_archive.yaml"
    parsed_path = root / "theblueprint_career_parsed.yaml"
    people_targets_path = root / "theblueprint_people_targets.yaml"
    route_resolutions_path = root / "theblueprint_route_resolutions.yaml"
    master_report_path = root / "theblueprint_master_report.md"

    archive_summary = _yaml_summary(archive_path)
    shortlist_summary = _yaml_summary(shortlist_path)
    route_summary = _yaml_summary(route_resolutions_path)
    people_targets = safe_read_yaml(people_targets_path)
    people_summary = people_targets.get("summary") or {}

    parser_counts = compact_counts(
        {
            "brands_crawled": int(archive_summary.get("brands_crawled_count") or 0),
            "listings": int(archive_summary.get("listing_count") or 0),
            "errors": int(archive_summary.get("errors_count") or archive_summary.get("errors") or 0),
        }
    )
    parser_status = derive_status(
        running=1 if "run_theblueprint_parser" in running_actions else 0,
        completed=int(parser_counts.get("brands_crawled") or 0),
        failed=int(parser_counts.get("errors") or 0),
    )

    shortlist_counts = compact_counts(
        {
            "selected": int(shortlist_summary.get("selected_company_count") or _count_listings(shortlist_path)),
            "segment_b": int(shortlist_summary.get("segment_B_count") or 0),
            "segment_c": int(shortlist_summary.get("segment_C_count") or 0),
            "segment_d": int(shortlist_summary.get("segment_D_count") or 0),
            "segment_e": int(shortlist_summary.get("segment_E_count") or 0),
        }
    )
    shortlist_status = derive_status(
        running=1 if "rebuild_theblueprint_shortlist" in running_actions else 0,
        completed=int(shortlist_counts.get("selected") or 0),
    )

    targets_count = int(people_summary.get("targets_count") or _count_listings(people_targets_path))
    people_counts = compact_counts(
        {
            "targets": targets_count,
            "wave_1": int(people_summary.get("wave_1_count") or 0),
            "wave_2": int(people_summary.get("wave_2_count") or 0),
            "wave_3": int(people_summary.get("wave_3_count") or 0),
        }
    )
    people_status = derive_status(
        running=1 if "build_theblueprint_people_targets" in running_actions else 0,
        completed=int(people_counts.get("targets") or 0),
    )

    route_counts = compact_counts(
        {
            "resolved_person_route": int(route_summary.get("resolved_person_route") or 0),
            "resolved_brand_route": int(route_summary.get("resolved_brand_route") or 0),
            "partial": int(route_summary.get("partial") or 0),
            "unresolved": int(route_summary.get("unresolved") or 0),
        }
    )
    route_status = derive_status(
        completed=int(route_counts.get("resolved_person_route") or 0) + int(route_counts.get("resolved_brand_route") or 0),
        queued=int(route_counts.get("unresolved") or 0),
        failed=0,
    )
    if int(route_counts.get("partial") or 0):
        route_status = "partial"

    master_report_exists = master_report_path.exists()
    master_status = "running" if "build_theblueprint_master_report" in running_actions else ("completed" if master_report_exists else "idle")

    nodes = [
        GraphNode(
            id="domain.company_contacts_enrichment",
            kind="domain",
            status="idle",
            label="Company Contacts",
            subtitle="The Blueprint archive, shortlist, routing, and reporting.",
            counts=compact_counts(
                {
                    "archive_companies": int(archive_summary.get("company_count") or 0),
                    "shortlisted": int(shortlist_counts.get("selected") or 0),
                    "resolved_routes": int(route_counts.get("resolved_person_route") or 0)
                    + int(route_counts.get("resolved_brand_route") or 0),
                }
            ),
            last_updated_at=latest_iso(
                [
                    path_mtime_iso(archive_path),
                    path_mtime_iso(shortlist_path),
                    path_mtime_iso(people_targets_path),
                    path_mtime_iso(route_resolutions_path),
                    path_mtime_iso(master_report_path),
                ]
            ),
            progress_text="Blueprint pipeline from archive crawl to outreach-ready report.",
            links=[
                make_link(project_root, "Archive", archive_path),
                make_link(project_root, "Shortlist input", shortlist_path),
                make_link(project_root, "Master report", master_report_path),
            ],
            position={"x": 700, "y": 120},
        ),
        GraphNode(
            id="contacts.blueprint_parser",
            kind="stage",
            status=parser_status,
            label="Blueprint Parser",
            subtitle="Full brand crawl across The Blueprint career archive.",
            counts=parser_counts,
            last_updated_at=path_mtime_iso(archive_path),
            progress_text="Pulls brand pages and vacancy listings into archive YAML.",
            links=[
                make_link(project_root, "Archive YAML", archive_path),
                make_link(project_root, "Parsed YAML", parsed_path),
            ],
            actions=[NodeActionRef(action_id="run_theblueprint_parser", label="Run parser")],
            position={"x": 90, "y": 240},
            metadata={"recent_items": _recent_lines_from_md(root / "theblueprint_outreach_report.md")},
        ),
        GraphNode(
            id="contacts.shortlist_reducer",
            kind="stage",
            status=shortlist_status,
            label="Shortlist Reducer",
            subtitle="Filters B/C/D/E targets and removes non-target noise.",
            counts=shortlist_counts,
            last_updated_at=path_mtime_iso(shortlist_path),
            progress_text="Produces the outreach working set from raw archive output.",
            links=[
                make_link(project_root, "Shortlist", shortlist_path),
                make_link(project_root, "Audit report", root / "theblueprint_career_audit.md"),
            ],
            actions=[NodeActionRef(action_id="rebuild_theblueprint_shortlist", label="Rebuild shortlist")],
            position={"x": 320, "y": 240},
        ),
        GraphNode(
            id="contacts.people_targets",
            kind="stage",
            status=people_status,
            label="People Targets",
            subtitle="Top targets with buyer, route, and wave priority.",
            counts=people_counts,
            last_updated_at=path_mtime_iso(people_targets_path),
            progress_text="Ranks who to contact first and why now.",
            links=[
                make_link(project_root, "People targets", people_targets_path),
                make_link(project_root, "People report", root / "theblueprint_people_targets_report.md"),
            ],
            actions=[NodeActionRef(action_id="build_theblueprint_people_targets", label="Build people targets")],
            position={"x": 550, "y": 240},
            metadata={"recent_items": _recent_lines_from_md(root / "theblueprint_people_targets_report.md")},
        ),
        GraphNode(
            id="contacts.route_resolver",
            kind="stage",
            status=route_status,
            label="Route Resolver",
            subtitle="Person -> Instagram -> Telegram -> site -> contacts trail.",
            counts=route_counts,
            last_updated_at=path_mtime_iso(route_resolutions_path),
            progress_text="Separates resolved, partial, and unresolved contact routes.",
            links=[
                make_link(project_root, "Route resolutions", route_resolutions_path),
                make_link(project_root, "Route report", root / "theblueprint_route_resolutions_report.md"),
            ],
            position={"x": 780, "y": 240},
        ),
        GraphNode(
            id="contacts.master_report",
            kind="stage",
            status=master_status,
            label="Master Report",
            subtitle="Single-file operator report with wave logic and noise notes.",
            counts=compact_counts({"available": 1 if master_report_exists else 0}),
            last_updated_at=path_mtime_iso(master_report_path),
            progress_text="Human-readable operating brief for the whole Blueprint flow.",
            links=[
                make_link(project_root, "Master report", master_report_path),
                make_link(project_root, "Outreach report", root / "theblueprint_outreach_report.md"),
            ],
            actions=[NodeActionRef(action_id="build_theblueprint_master_report", label="Build master report")],
            position={"x": 1010, "y": 240},
            metadata={"recent_items": _recent_lines_from_md(master_report_path)},
        ),
    ]

    edges = [
        GraphEdge(id="cc-1", source="contacts.blueprint_parser", target="contacts.shortlist_reducer"),
        GraphEdge(id="cc-2", source="contacts.shortlist_reducer", target="contacts.people_targets"),
        GraphEdge(id="cc-3", source="contacts.people_targets", target="contacts.route_resolver"),
        GraphEdge(id="cc-4", source="contacts.route_resolver", target="contacts.master_report"),
    ]
    domain_status = aggregate_status([node.status for node in nodes[1:]])
    nodes[0].status = domain_status
    return GraphView(
        id="company_contacts_enrichment",
        label="Company Contacts Enrichment",
        subtitle="The Blueprint archive, reducer, route resolver, and operator reporting.",
        status=domain_status,
        nodes=nodes,
        edges=edges,
        metadata={"domain_id": "company_contacts_enrichment"},
    )
