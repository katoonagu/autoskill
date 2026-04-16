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


def build_outreach_view(project_root: Path, *, running_actions: set[str] | None = None) -> GraphView:
    running_actions = running_actions or set()
    artifact_root = artifacts_root(project_root)
    state_root = runtime_state_root(project_root)

    brand_search_state = safe_read_json(state_root / "instagram_brand_search_state.json")
    dm_state = safe_read_json(state_root / "instagram_dm_outreach_state.json")
    dm_status = safe_read_json(artifact_root / "instagram_dm_outreach" / "status_report.json")
    mail_state = safe_read_json(state_root / "mail_outreach_state.json")
    mail_registry = safe_read_json(artifact_root / "mail_outreach" / "inbox_audit.json")
    conversation_state = safe_read_json(state_root / "conversation_state.json")

    instagram_brand_counts = compact_counts(
        {
            "completed": len(brand_search_state.get("completed_brand_handles") or []),
            "profiles": len(brand_search_state.get("brand_handles") or []),
        }
    )
    instagram_brand_status = derive_status(
        completed=int(instagram_brand_counts.get("completed") or 0),
        running=1 if brand_search_state.get("current_profile_no") else 0,
    )

    dm_rows = dm_status.get("rows") or []
    dm_counts = compact_counts(
        {
            "targets": len(dm_rows),
            "sent_only": sum(1 for item in dm_rows if str(item.get("status") or "") == "thread_found_sent_only"),
            "reply_detected": sum(1 for item in dm_rows if bool(item.get("reply_detected"))),
        }
    )
    dm_node_status = derive_status(
        running=1 if (dm_state.get("current_target_url") or "") else 0,
        completed=int(dm_counts.get("targets") or 0),
    )
    if int(dm_counts.get("sent_only") or 0):
        dm_node_status = "partial"

    mail_rows = mail_registry if isinstance(mail_registry, list) else []
    mail_counts = compact_counts(
        {
            "contacts": len(mail_rows),
            "reply_unread": sum(1 for item in mail_rows if str(item.get("status") or "") == "reply_unread"),
            "thread_found_sent_only": sum(
                1 for item in mail_rows if str(item.get("status") or "") == "thread_found_sent_only"
            ),
        }
    )
    mail_node_status = derive_status(
        running=1 if (mail_state.get("current_email") or "") else 0,
        completed=int(mail_counts.get("contacts") or 0),
    )
    if int(mail_counts.get("reply_unread") or 0) or int(mail_counts.get("thread_found_sent_only") or 0):
        mail_node_status = "partial"

    conversation_threads = conversation_state.get("threads") or {}
    conversation_counts = compact_counts(
        {
            "threads": len(conversation_threads),
            "draft_ready": sum(1 for item in conversation_threads.values() if str(item.get("status") or "") == "draft_ready"),
        }
    )
    conversation_status = derive_status(
        waiting_approval=int(conversation_counts.get("draft_ready") or 0),
        completed=int(conversation_counts.get("threads") or 0),
    )
    if int(conversation_counts.get("draft_ready") or 0):
        conversation_status = "waiting_approval"

    nodes = [
        GraphNode(
            id="domain.outreach_execution",
            kind="domain",
            status="idle",
            label="Outreach Execution",
            subtitle="Discovery outputs, DM/mail sends, and conversation status.",
            counts=compact_counts(
                {
                    "dm_targets": int(dm_counts.get("targets") or 0),
                    "mail_contacts": int(mail_counts.get("contacts") or 0),
                    "threads": int(conversation_counts.get("threads") or 0),
                }
            ),
            last_updated_at=latest_iso(
                [
                    path_mtime_iso(state_root / "instagram_brand_search_state.json"),
                    path_mtime_iso(artifact_root / "instagram_dm_outreach" / "status_report.json"),
                    path_mtime_iso(state_root / "mail_outreach_state.json"),
                    path_mtime_iso(state_root / "conversation_state.json"),
                ]
            ),
            progress_text="Operational view of outbound contact channels.",
            links=[
                make_link(project_root, "DM status", artifact_root / "instagram_dm_outreach" / "status_report.json"),
                make_link(project_root, "Mail inbox audit", artifact_root / "mail_outreach" / "inbox_audit.json"),
                make_link(project_root, "Conversation state", state_root / "conversation_state.json"),
            ],
            position={"x": 720, "y": 120},
        ),
        GraphNode(
            id="outreach.instagram_brand_search",
            kind="stage",
            status=instagram_brand_status,
            label="Instagram Brand Search",
            subtitle="Lead discovery and evidence capture.",
            counts=instagram_brand_counts,
            last_updated_at=path_mtime_iso(state_root / "instagram_brand_search_state.json"),
            progress_text="Feeds brand handles and source evidence into the system.",
            links=[
                make_link(project_root, "Brand search state", state_root / "instagram_brand_search_state.json"),
                make_link(project_root, "Runner", project_root / "scripts" / "run_instagram_brand_search.py"),
            ],
            position={"x": 120, "y": 240},
            metadata={
                "recent_items": [
                    item for item in (brand_search_state.get("completed_brand_handles") or [])[-5:]
                ]
            },
        ),
        GraphNode(
            id="outreach.instagram_dm",
            kind="stage",
            status=dm_node_status,
            label="DM Outreach",
            subtitle="Profile-popup sends and thread audits.",
            counts=dm_counts,
            last_updated_at=path_mtime_iso(artifact_root / "instagram_dm_outreach" / "status_report.json"),
            progress_text="Tracks sent-only DM threads and reply detection.",
            links=[
                make_link(project_root, "DM status", artifact_root / "instagram_dm_outreach" / "status_report.json"),
                make_link(project_root, "DM state", state_root / "instagram_dm_outreach_state.json"),
            ],
            actions=[NodeActionRef(action_id="audit_instagram_dm_targets", label="Audit DM targets")],
            position={"x": 420, "y": 240},
            metadata={
                "recent_items": [
                    f"{item.get('handle', 'target')}: {item.get('status', 'unknown')}"
                    for item in dm_rows[:5]
                ]
            },
        ),
        GraphNode(
            id="outreach.mail_outreach",
            kind="stage",
            status=mail_node_status,
            label="Mail Outreach",
            subtitle="Mailbox sends and inbox follow-up audit.",
            counts=mail_counts,
            last_updated_at=latest_iso(
                [
                    path_mtime_iso(state_root / "mail_outreach_state.json"),
                    path_mtime_iso(artifact_root / "mail_outreach" / "inbox_audit.json"),
                ]
            ),
            progress_text="Audits replies, sent-only threads, and unread responses.",
            links=[
                make_link(project_root, "Mail state", state_root / "mail_outreach_state.json"),
                make_link(project_root, "Inbox audit", artifact_root / "mail_outreach" / "inbox_audit.json"),
                make_link(project_root, "Contact registry", artifact_root / "mail_outreach" / "contact_registry.json"),
            ],
            position={"x": 720, "y": 240},
            metadata={
                "recent_items": [
                    f"{item.get('email', 'email')}: {item.get('status', 'unknown')}"
                    for item in mail_rows[:5]
                ]
            },
        ),
        GraphNode(
            id="outreach.conversation_status",
            kind="stage",
            status=conversation_status,
            label="Conversation Status",
            subtitle="Thread draft readiness and next action.",
            counts=conversation_counts,
            last_updated_at=path_mtime_iso(state_root / "conversation_state.json"),
            progress_text="Shows which message threads are blocked on approval or ready to move.",
            links=[
                make_link(project_root, "Conversation state", state_root / "conversation_state.json"),
                make_link(project_root, "Conversation artifacts", artifact_root / "conversation", kind="directory"),
            ],
            position={"x": 1020, "y": 240},
            metadata={
                "recent_items": [
                    f"{key}: {value.get('status', 'unknown')}"
                    for key, value in list(conversation_threads.items())[:5]
                ]
            },
        ),
    ]
    edges = [
        GraphEdge(id="oe-1", source="outreach.instagram_brand_search", target="outreach.instagram_dm"),
        GraphEdge(id="oe-2", source="outreach.instagram_brand_search", target="outreach.mail_outreach"),
        GraphEdge(id="oe-3", source="outreach.instagram_dm", target="outreach.conversation_status"),
        GraphEdge(id="oe-4", source="outreach.mail_outreach", target="outreach.conversation_status"),
    ]
    domain_status = aggregate_status([node.status for node in nodes[1:]])
    nodes[0].status = domain_status
    return GraphView(
        id="outreach_execution",
        label="Outreach Execution",
        subtitle="Instagram and mail operations plus live conversation state.",
        status=domain_status,
        nodes=nodes,
        edges=edges,
        metadata={"domain_id": "outreach_execution"},
    )
