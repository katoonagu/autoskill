from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automation.paths import artifacts_root

from .actions import ActionRegistry
from .docs_loader import load_node_doc
from .models import GraphNode, GraphView, NodeActionRef, NodeDetail
from .sources import (
    build_company_contacts_view,
    build_knowledge_view,
    build_outreach_view,
    build_runtime_view,
    build_supervisor_view,
)
from .utils import aggregate_status, append_markdown_section, compact_counts, utcnow_iso

DOMAIN_ORDER = [
    "control_plane",
    "company_contacts_enrichment",
    "outreach_execution",
    "browser_runtime",
    "knowledge_reports",
]

OVERVIEW_POSITIONS = {
    "control_plane": {"x": 620, "y": 120},
    "company_contacts_enrichment": {"x": 180, "y": 320},
    "outreach_execution": {"x": 1060, "y": 320},
    "browser_runtime": {"x": 360, "y": 540},
    "knowledge_reports": {"x": 880, "y": 540},
}


def _links_markdown(links: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in links:
        label = str(item.get("label") or "Link")
        path = str(item.get("path") or "")
        kind = str(item.get("kind") or "file")
        if not path:
            continue
        lines.append(f"- `{label}` ({kind}) -> `{path}`")
    return lines


def _status_markdown(detail: NodeDetail) -> list[str]:
    lines = [
        f"- Status: `{detail.status}`",
        f"- Last updated: `{detail.last_updated_at or 'n/a'}`",
    ]
    if detail.progress_text:
        lines.append(f"- Progress: {detail.progress_text}")
    if detail.counts:
        lines.append(f"- Counts: `{json.dumps(detail.counts, ensure_ascii=False)}`")
    return lines


def _detail_for_node(project_root: Path, domain_id: str, node: GraphNode) -> NodeDetail:
    recent_items = node.metadata.get("recent_items") if isinstance(node.metadata, dict) else []
    doc = load_node_doc(project_root, node.id).strip()
    body_lines = [doc]
    detail = NodeDetail(
        node_id=node.id,
        domain_id=domain_id,
        status=node.status,
        label=node.label,
        subtitle=node.subtitle,
        counts=node.counts,
        last_updated_at=node.last_updated_at,
        progress_text=node.progress_text,
        detail_markdown="",
        links=node.links,
        actions=node.actions,
        metadata=node.metadata,
    )
    append_markdown_section(body_lines, "Live Status", _status_markdown(detail))
    if recent_items:
        append_markdown_section(body_lines, "Recent Items", [f"- {item}" for item in recent_items[:10]])
    append_markdown_section(body_lines, "Source of Truth", _links_markdown([item.to_dict() for item in node.links]))
    detail.detail_markdown = "\n".join(body_lines).strip() + "\n"
    return detail


def _overview_view(views: dict[str, GraphView], actions_by_group: dict[str, list[NodeActionRef]]) -> GraphView:
    nodes: list[GraphNode] = []
    edges = []
    edge_pairs = [
        ("domain.control_plane", "domain.company_contacts_enrichment"),
        ("domain.control_plane", "domain.outreach_execution"),
        ("domain.company_contacts_enrichment", "domain.knowledge_reports"),
        ("domain.outreach_execution", "domain.browser_runtime"),
        ("domain.browser_runtime", "domain.knowledge_reports"),
    ]
    for index, (source, target) in enumerate(edge_pairs, start=1):
        edges.append(
            __import__("automation.visualization.models", fromlist=["GraphEdge"]).GraphEdge(
                id=f"overview-{index}",
                source=source,
                target=target,
            )
        )

    for domain_id in DOMAIN_ORDER:
        view = views[domain_id]
        domain_node = next(node for node in view.nodes if node.kind == "domain")
        nodes.append(
            GraphNode(
                id=domain_node.id,
                kind="domain",
                status=view.status,
                label=view.label,
                subtitle=view.subtitle,
                counts=domain_node.counts,
                last_updated_at=domain_node.last_updated_at,
                progress_text=domain_node.progress_text,
                links=domain_node.links,
                actions=actions_by_group.get(domain_id, []),
                position=OVERVIEW_POSITIONS[domain_id],
                metadata=domain_node.metadata,
            )
        )
    return GraphView(
        id="overview",
        label="AUTOSKILL",
        subtitle="Live map of the repo's automation domains, runtime, and reports.",
        status=aggregate_status([view.status for view in views.values()]),
        nodes=nodes,
        edges=edges,
        metadata={"domain_order": DOMAIN_ORDER},
    )


def _actions_by_group(action_payloads: list[dict[str, Any]]) -> dict[str, list[NodeActionRef]]:
    mapping: dict[str, list[NodeActionRef]] = {
        "control_plane": [],
        "company_contacts_enrichment": [],
        "outreach_execution": [],
        "browser_runtime": [],
        "knowledge_reports": [],
    }
    for item in action_payloads:
        group = str(item.get("group") or "")
        if group not in mapping:
            continue
        mapping[group].append(
            NodeActionRef(
                action_id=str(item.get("id") or ""),
                label=str(item.get("label") or "Launch"),
            )
        )
    return mapping


def build_agent_canvas_bundle(project_root: Path, *, action_registry: ActionRegistry | None = None) -> dict[str, Any]:
    registry = action_registry or ActionRegistry(project_root)
    action_runs = registry.refresh_runs()
    actions = registry.list_actions()
    running_actions = {
        str(item.get("action_id") or "")
        for item in action_runs
        if str(item.get("status") or "") == "running"
    }

    views = {
        "control_plane": build_supervisor_view(project_root, running_actions=running_actions),
        "company_contacts_enrichment": build_company_contacts_view(project_root, running_actions=running_actions),
        "outreach_execution": build_outreach_view(project_root, running_actions=running_actions),
        "browser_runtime": build_runtime_view(project_root, running_actions=running_actions),
        "knowledge_reports": build_knowledge_view(project_root, running_actions=running_actions),
    }
    overview = _overview_view(views, _actions_by_group(actions))

    node_details: dict[str, dict[str, Any]] = {}
    for domain_id, view in views.items():
        for node in view.nodes:
            detail = _detail_for_node(project_root, domain_id, node)
            node_details[node.id] = detail.to_dict()
    for node in overview.nodes:
        if node.id not in node_details:
            node_details[node.id] = _detail_for_node(project_root, "overview", node).to_dict()

    return {
        "generated_at": utcnow_iso(),
        "overview": overview.to_dict(),
        "domains": {key: value.to_dict() for key, value in views.items()},
        "nodes": node_details,
        "actions": actions,
        "action_runs": action_runs,
        "summary": compact_counts(
            {
                "domains": len(views),
                "running_actions": len(running_actions),
                "running_nodes": sum(
                    1
                    for view in views.values()
                    for node in view.nodes
                    if node.status == "running"
                ),
            }
        ),
    }


def write_agent_canvas_bundle(project_root: Path, *, action_registry: ActionRegistry | None = None) -> dict[str, Any]:
    bundle = build_agent_canvas_bundle(project_root, action_registry=action_registry)
    out_root = artifacts_root(project_root) / "agent_canvas"
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "graph_manifest.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for domain_id, view in bundle["domains"].items():
        (out_root / f"domain_{domain_id}.json").write_text(
            json.dumps(view, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (out_root / "node_index.json").write_text(
        json.dumps(bundle["nodes"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "action_runs.json").write_text(
        json.dumps({"runs": bundle["action_runs"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bundle
