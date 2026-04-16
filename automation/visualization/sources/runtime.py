from __future__ import annotations

from automation.paths import artifacts_root, runtime_state_root

from ..models import GraphEdge, GraphNode, GraphView
from ..utils import (
    aggregate_status,
    compact_counts,
    latest_iso,
    list_recent_files,
    make_link,
    path_mtime_iso,
)


def build_runtime_view(project_root, *, running_actions: set[str] | None = None) -> GraphView:
    del running_actions
    state_root = runtime_state_root(project_root)
    artifact_root = artifacts_root(project_root)

    profile_pool = project_root / "automation" / "agents" / "profile_pool.yaml"
    agent_registry = project_root / "automation" / "agents" / "registry.yaml"
    lease_root = state_root / "leases"
    playwright_root = artifact_root / "playwright"

    lease_files = list(lease_root.glob("*.json")) if lease_root.exists() else []
    recent_playwright = list_recent_files(playwright_root, "*", limit=5)

    profile_count = 0
    if profile_pool.exists():
        import yaml

        payload = yaml.safe_load(profile_pool.read_text(encoding="utf-8-sig")) or {}
        profiles = payload.get("profiles") or {}
        profile_count = len(profiles) if isinstance(profiles, dict) else 0

    nodes = [
        GraphNode(
            id="domain.browser_runtime",
            kind="domain",
            status="idle",
            label="Browser Runtime",
            subtitle="Profiles, leases, and Playwright run directories.",
            counts=compact_counts(
                {
                    "profiles": profile_count,
                    "leases": len(lease_files),
                    "playwright_runs": sum(1 for _ in playwright_root.iterdir()) if playwright_root.exists() else 0,
                }
            ),
            last_updated_at=latest_iso(
                [
                    path_mtime_iso(profile_pool),
                    path_mtime_iso(agent_registry),
                    latest_iso([path_mtime_iso(item) for item in lease_files]),
                    latest_iso([path_mtime_iso(item) for item in recent_playwright]),
                ]
            ),
            progress_text="Operational substrate for browser work and automation sessions.",
            links=[
                make_link(project_root, "Profile pool", profile_pool),
                make_link(project_root, "Playwright artifacts", playwright_root, kind="directory"),
            ],
            position={"x": 720, "y": 120},
        ),
        GraphNode(
            id="runtime.adspower_profiles",
            kind="resource",
            status="completed" if profile_count else "idle",
            label="AdsPower Profiles",
            subtitle="Named browser capabilities and reserved roles.",
            counts=compact_counts({"profiles": profile_count}),
            last_updated_at=latest_iso([path_mtime_iso(profile_pool), path_mtime_iso(agent_registry)]),
            progress_text="Maps logical runtime roles onto configured browser profiles.",
            links=[
                make_link(project_root, "Profile pool", profile_pool),
                make_link(project_root, "Agent registry", agent_registry),
            ],
            position={"x": 160, "y": 240},
        ),
        GraphNode(
            id="runtime.profile_leases",
            kind="resource",
            status="running" if lease_files else "idle",
            label="Profile Leases",
            subtitle="Runtime locks and hand-offs for browser ownership.",
            counts=compact_counts({"leases": len(lease_files)}),
            last_updated_at=latest_iso([path_mtime_iso(item) for item in lease_files]),
            progress_text="Shows whether any browser profiles are actively reserved.",
            links=[
                make_link(project_root, "Lease directory", lease_root, kind="directory"),
            ],
            position={"x": 500, "y": 240},
            metadata={"recent_items": [item.name for item in lease_files[:5]]},
        ),
        GraphNode(
            id="runtime.playwright_runs",
            kind="resource",
            status="completed" if recent_playwright else "idle",
            label="Playwright Runs",
            subtitle="Recent screenshot and browser automation traces.",
            counts=compact_counts({"runs": sum(1 for _ in playwright_root.iterdir()) if playwright_root.exists() else 0}),
            last_updated_at=latest_iso([path_mtime_iso(item) for item in recent_playwright]),
            progress_text="Surface recent browser runs, screenshots, and debug sessions.",
            links=[
                make_link(project_root, "Playwright artifact root", playwright_root, kind="directory"),
            ],
            position={"x": 840, "y": 240},
            metadata={"recent_items": [item.name for item in recent_playwright]},
        ),
    ]
    edges = [
        GraphEdge(id="rt-1", source="runtime.adspower_profiles", target="runtime.profile_leases"),
        GraphEdge(id="rt-2", source="runtime.profile_leases", target="runtime.playwright_runs"),
    ]
    domain_status = aggregate_status([node.status for node in nodes[1:]])
    nodes[0].status = domain_status
    return GraphView(
        id="browser_runtime",
        label="Browser Runtime",
        subtitle="Profiles, leases, and Playwright execution traces.",
        status=domain_status,
        nodes=nodes,
        edges=edges,
        metadata={"domain_id": "browser_runtime"},
    )
