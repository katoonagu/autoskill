from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GraphLink:
    label: str
    path: str
    kind: str = "file"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NodeActionRef:
    action_id: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNode:
    id: str
    kind: str
    status: str
    label: str
    subtitle: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    last_updated_at: str = ""
    progress_text: str = ""
    detail_markdown: str = ""
    links: list[GraphLink] = field(default_factory=list)
    actions: list[NodeActionRef] = field(default_factory=list)
    position: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["links"] = [item.to_dict() for item in self.links]
        payload["actions"] = [item.to_dict() for item in self.actions]
        return payload


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphView:
    id: str
    label: str
    subtitle: str
    status: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "subtitle": self.subtitle,
            "status": self.status,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "metadata": self.metadata,
        }


@dataclass
class NodeDetail:
    node_id: str
    domain_id: str
    status: str
    label: str
    subtitle: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    last_updated_at: str = ""
    progress_text: str = ""
    detail_markdown: str = ""
    links: list[GraphLink] = field(default_factory=list)
    actions: list[NodeActionRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "domain_id": self.domain_id,
            "status": self.status,
            "label": self.label,
            "subtitle": self.subtitle,
            "counts": self.counts,
            "last_updated_at": self.last_updated_at,
            "progress_text": self.progress_text,
            "detail_markdown": self.detail_markdown,
            "links": [item.to_dict() for item in self.links],
            "actions": [item.to_dict() for item in self.actions],
            "metadata": self.metadata,
        }


@dataclass
class LaunchAction:
    id: str
    label: str
    description: str
    command: list[str]
    group: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionRun:
    run_id: str
    action_id: str
    label: str
    status: str
    started_at: str
    finished_at: str = ""
    exit_code: int | None = None
    log_path: str = ""
    pid: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
