from __future__ import annotations

from pathlib import Path

from automation.paths import artifacts_root, runtime_state_root

from ..models import GraphEdge, GraphNode, GraphView, NodeActionRef
from ..utils import (
    aggregate_status,
    compact_counts,
    derive_status,
    latest_iso,
    make_link,
    path_mtime_iso,
    safe_read_json,
)


def _state_summary(path: Path, *, completed_key: str = "completed_brand_handles", current_key: str = "current_brand_handle") -> tuple[dict[str, int], str]:
    payload = safe_read_json(path)
    current_item = str(payload.get(current_key) or "")
    completed_items = payload.get(completed_key) or []
    completed_count = len(completed_items) if isinstance(completed_items, list) else 0
    running = 1 if current_item else 0
    counts = compact_counts({"running": running, "completed": completed_count})
    status = derive_status(running=running, completed=completed_count)
    return counts, status


def _make_stage(
    *,
    node_id: str,
    label: str,
    subtitle: str,
    status: str,
    counts: dict[str, int],
    project_root: Path,
    position: dict[str, float],
    links: list,
    action_id: str | None = None,
    progress_text: str = "",
    last_updated_at: str = "",
    recent_items: list[str] | None = None,
) -> GraphNode:
    actions = [NodeActionRef(action_id=action_id, label="Launch")] if action_id else []
    return GraphNode(
        id=node_id,
        kind="stage",
        status=status,
        label=label,
        subtitle=subtitle,
        counts=counts,
        last_updated_at=last_updated_at,
        progress_text=progress_text,
        links=links,
        actions=actions,
        position=position,
        metadata={"recent_items": recent_items or []},
    )


def build_supervisor_view(project_root: Path, *, running_actions: set[str] | None = None) -> GraphView:
    running_actions = running_actions or set()
    supervisor_root = artifacts_root(project_root) / "supervisor"
    status_report = safe_read_json(supervisor_root / "status_report.json")
    workboard = safe_read_json(supervisor_root / "codex_workboard.json")
    run_summary = safe_read_json(supervisor_root / "run_summary.json")
    state_root = runtime_state_root(project_root)

    task_counts = status_report.get("task_counts") or {}
    approval_counts = status_report.get("approval_counts") or {}
    recent_completed = status_report.get("recent_completed") or []

    discovery_counts, discovery_status = _state_summary(state_root / "instagram_brand_search_state.json")
    brand_intelligence_counts, brand_intelligence_status = _state_summary(state_root / "brand_intelligence_state.json")
    brand_arbiter_counts = compact_counts(
        {
            "completed": sum(
                1
                for item in recent_completed
                if str(item.get("assigned_agent") or "") == "brand_arbiter_agent"
            )
        }
    )
    brand_arbiter_status = "completed" if brand_arbiter_counts else "idle"

    media_counts, media_status = _state_summary(
        state_root / "media_intelligence_state.json",
        completed_key="completed_brand_handles",
        current_key="current_brand_handle",
    )

    planning_counts = compact_counts(
        {
            "queued": len(workboard.get("ready_for_planning") or []),
            "waiting_approval": len(workboard.get("waiting_approval") or []),
            "sent": len(workboard.get("sent") or []),
        }
    )
    planning_status = derive_status(
        queued=int(planning_counts.get("queued") or 0),
        waiting_approval=int(planning_counts.get("waiting_approval") or 0),
        completed=int(planning_counts.get("sent") or 0),
    )

    conversation_state = safe_read_json(state_root / "conversation_state.json")
    conversation_threads = conversation_state.get("threads") or {}
    draft_ready = sum(1 for item in conversation_threads.values() if str(item.get("status") or "") == "draft_ready")
    conversation_counts = compact_counts(
        {
            "draft_ready": draft_ready,
            "waiting_approval": len(status_report.get("pending_approvals") or []),
            "completed": len(conversation_state.get("completed_conversation_keys") or []),
        }
    )
    conversation_status = derive_status(
        waiting_approval=int(conversation_counts.get("waiting_approval") or 0),
        completed=int(conversation_counts.get("completed") or 0),
    )
    if draft_ready and conversation_status == "idle":
        conversation_status = "partial"

    feedback_counts, feedback_status = _state_summary(
        state_root / "feedback_validation_state.json",
        completed_key="completed_brand_handles",
        current_key="current_brand_handle",
    )

    codex_review_counts = compact_counts(
        {
            "waiting_review": int(task_counts.get("waiting_codex_review") or 0),
            "in_review": int(task_counts.get("codex_reviewing") or 0),
        }
    )
    codex_review_status = derive_status(
        waiting_review=int(codex_review_counts.get("waiting_review") or 0),
        completed=int(run_summary.get("moved_to_codex_review") or 0),
    )

    approval_node_counts = compact_counts(
        {
            "waiting_approval": int(approval_counts.get("pending") or 0),
            "approved": int(approval_counts.get("approved") or 0),
            "rejected": int(approval_counts.get("rejected") or 0),
        }
    )
    approval_status = derive_status(
        waiting_approval=int(approval_node_counts.get("waiting_approval") or 0),
        completed=int(approval_node_counts.get("approved") or 0),
        failed=int(approval_node_counts.get("rejected") or 0),
    )

    if "run_supervisor" in running_actions:
        discovery_status = "running"
        brand_intelligence_status = "running" if brand_intelligence_status == "idle" else brand_intelligence_status

    shared_links = [
        make_link(project_root, "Supervisor status", supervisor_root / "status_report.json"),
        make_link(project_root, "Codex workboard", supervisor_root / "codex_workboard.json"),
        make_link(project_root, "Run summary", supervisor_root / "run_summary.json"),
        make_link(project_root, "Task runtime", project_root / "runtime" / "tasks", kind="directory"),
    ]

    recent_labels = [
        f"{item.get('assigned_agent', 'agent')} -> {item.get('task_id', 'task')}"
        for item in recent_completed[:5]
    ]
    nodes = [
        GraphNode(
            id="domain.control_plane",
            kind="domain",
            status="idle",
            label="Control Plane",
            subtitle="Supervisor, approvals, and routed agent work.",
            counts=compact_counts(
                {
                    "inbox": int(task_counts.get("inbox") or 0),
                    "completed": int(task_counts.get("completed") or 0),
                    "pending_approvals": int(approval_counts.get("pending") or 0),
                }
            ),
            last_updated_at=latest_iso(
                [
                    path_mtime_iso(supervisor_root / "status_report.json"),
                    path_mtime_iso(supervisor_root / "codex_workboard.json"),
                    path_mtime_iso(supervisor_root / "run_summary.json"),
                ]
            ),
            progress_text=f"Brain mode: {run_summary.get('brain_mode') or 'unknown'}",
            links=shared_links,
            position={"x": 760, "y": 120},
            metadata={"recent_items": recent_labels},
        ),
        _make_stage(
            node_id="control.discovery",
            label="Discovery",
            subtitle="Instagram-first brand discovery intake.",
            status=discovery_status,
            counts=discovery_counts,
            project_root=project_root,
            position={"x": 80, "y": 220},
            links=[
                make_link(project_root, "Discovery state", state_root / "instagram_brand_search_state.json"),
                make_link(project_root, "Registry", project_root / "automation" / "agents" / "registry.yaml"),
            ],
            progress_text="Collects brand handles, evidence, and mentions.",
            last_updated_at=path_mtime_iso(state_root / "instagram_brand_search_state.json"),
        ),
        _make_stage(
            node_id="control.brand_intelligence",
            label="Brand Intelligence",
            subtitle="Evidence normalization and dossier build.",
            status=brand_intelligence_status,
            counts=brand_intelligence_counts,
            project_root=project_root,
            position={"x": 260, "y": 220},
            links=[
                make_link(project_root, "Brand intelligence state", state_root / "brand_intelligence_state.json"),
                make_link(project_root, "Brand artifacts", project_root / "artifacts" / "brand_intelligence", kind="directory"),
            ],
            progress_text="Builds evidence bundles and dossiers.",
            last_updated_at=path_mtime_iso(state_root / "brand_intelligence_state.json"),
        ),
        _make_stage(
            node_id="control.brand_arbiter",
            label="Brand Arbiter",
            subtitle="Main reasoning layer and verdict packet.",
            status=brand_arbiter_status,
            counts=brand_arbiter_counts,
            project_root=project_root,
            position={"x": 460, "y": 220},
            links=[
                make_link(project_root, "Supervisor status", supervisor_root / "status_report.json"),
                make_link(project_root, "Arbiter artifacts", project_root / "artifacts" / "brand_arbiter", kind="directory"),
            ],
            progress_text="Turns evidence into go/no-go decisions.",
            last_updated_at=path_mtime_iso(supervisor_root / "status_report.json"),
            recent_items=recent_labels,
        ),
        _make_stage(
            node_id="control.media_intelligence",
            label="Media Intelligence",
            subtitle="Optional deep media and fit analysis.",
            status=media_status,
            counts=media_counts,
            project_root=project_root,
            position={"x": 660, "y": 220},
            links=[
                make_link(project_root, "Media intelligence state", state_root / "media_intelligence_state.json"),
                make_link(project_root, "Media artifacts", project_root / "artifacts" / "media_intelligence", kind="directory"),
            ],
            progress_text="Triggered when a case needs extra context.",
            last_updated_at=path_mtime_iso(state_root / "media_intelligence_state.json"),
        ),
        _make_stage(
            node_id="control.outreach_planning",
            label="Outreach Planning",
            subtitle="Channel choice, targeting, and personalization.",
            status=planning_status,
            counts=planning_counts,
            project_root=project_root,
            position={"x": 860, "y": 220},
            links=[
                make_link(project_root, "Codex workboard", supervisor_root / "codex_workboard.json"),
                make_link(project_root, "Planning artifacts", project_root / "artifacts" / "outreach_planning", kind="directory"),
            ],
            progress_text="Routes ready cases into contact plans.",
            last_updated_at=path_mtime_iso(supervisor_root / "codex_workboard.json"),
        ),
        _make_stage(
            node_id="control.conversation",
            label="Conversation",
            subtitle="Draft preparation and approved send queue.",
            status=conversation_status,
            counts=conversation_counts,
            project_root=project_root,
            position={"x": 1060, "y": 220},
            links=[
                make_link(project_root, "Conversation state", state_root / "conversation_state.json"),
                make_link(project_root, "Conversation artifacts", project_root / "artifacts" / "conversation", kind="directory"),
            ],
            progress_text="Tracks drafts and waiting send approvals.",
            last_updated_at=path_mtime_iso(state_root / "conversation_state.json"),
        ),
        _make_stage(
            node_id="control.feedback_validation",
            label="Feedback Validation",
            subtitle="Review, complaints, and follow-up validation.",
            status=feedback_status,
            counts=feedback_counts,
            project_root=project_root,
            position={"x": 1260, "y": 220},
            links=[
                make_link(project_root, "Feedback state", state_root / "feedback_validation_state.json"),
                make_link(project_root, "Validation artifacts", project_root / "artifacts" / "feedback_validation", kind="directory"),
            ],
            progress_text="Checks external signals before escalation.",
            last_updated_at=path_mtime_iso(state_root / "feedback_validation_state.json"),
        ),
        GraphNode(
            id="control.codex_review",
            kind="approval_gate",
            status=codex_review_status,
            label="Codex Review",
            subtitle="Ready-for-review and in-review task batches.",
            counts=codex_review_counts,
            last_updated_at=path_mtime_iso(supervisor_root / "codex_workboard.json"),
            progress_text="Human-assisted review before planning or send.",
            links=[
                make_link(project_root, "Codex workboard", supervisor_root / "codex_workboard.json"),
                make_link(project_root, "Review batches", supervisor_root / "codex_review_batches", kind="directory"),
            ],
            position={"x": 960, "y": 380},
            metadata={"recent_items": recent_labels},
        ),
        GraphNode(
            id="control.human_approval",
            kind="approval_gate",
            status=approval_status,
            label="Human Approval",
            subtitle="Pending send approvals and decisions.",
            counts=approval_node_counts,
            last_updated_at=path_mtime_iso(supervisor_root / "status_report.json"),
            progress_text="Explicit approval checkpoint before outbound contact.",
            links=[
                make_link(project_root, "Approvals index", project_root / "artifacts" / "supervisor" / "approvals_index.json"),
                make_link(project_root, "Status report", supervisor_root / "status_report.json"),
            ],
            position={"x": 1160, "y": 380},
            metadata={
                "recent_items": [
                    str(item.get("approval_id") or "")
                    for item in (status_report.get("pending_approvals") or [])[:5]
                    if item.get("approval_id")
                ]
            },
        ),
    ]
    edges = [
        GraphEdge(id="cp-1", source="control.discovery", target="control.brand_intelligence"),
        GraphEdge(id="cp-2", source="control.brand_intelligence", target="control.brand_arbiter"),
        GraphEdge(id="cp-3", source="control.brand_arbiter", target="control.media_intelligence"),
        GraphEdge(id="cp-4", source="control.media_intelligence", target="control.outreach_planning"),
        GraphEdge(id="cp-5", source="control.outreach_planning", target="control.conversation"),
        GraphEdge(id="cp-6", source="control.conversation", target="control.feedback_validation"),
        GraphEdge(id="cp-7", source="control.outreach_planning", target="control.codex_review"),
        GraphEdge(id="cp-8", source="control.codex_review", target="control.human_approval"),
        GraphEdge(id="cp-9", source="control.human_approval", target="control.conversation"),
    ]

    domain_status = aggregate_status([node.status for node in nodes[1:]])
    nodes[0].status = domain_status
    return GraphView(
        id="control_plane",
        label="Control Plane",
        subtitle="Supervisor orchestration across discovery, review, planning, and approvals.",
        status=domain_status,
        nodes=nodes,
        edges=edges,
        metadata={"domain_id": "control_plane"},
    )
