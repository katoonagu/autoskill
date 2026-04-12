from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentTask:
    task_id: str
    task_type: str
    assigned_agent: str
    status: str = "pending"
    priority: str = "normal"
    created_at_iso: str = ""
    updated_at_iso: str = ""
    source_run_id: str = ""
    source_task_id: str = ""
    entity_refs: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 1
    requires_browser: bool = False
    required_profile_capability: str = ""
    requires_human_approval: bool = False
    approval_scope: str = ""
    blocked_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTask":
        return cls(**data)


@dataclass
class TaskSpawn:
    task_type: str
    entity_refs: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    source_task_id: str = ""
    source_run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    task_id: str
    agent: str
    status: str
    completed_at_iso: str
    summary: str = ""
    confidence: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    decision_refs: list[str] = field(default_factory=list)
    next_tasks: list[TaskSpawn] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["next_tasks"] = [task.to_dict() for task in self.next_tasks]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        next_tasks = [TaskSpawn(**item) for item in data.get("next_tasks", [])]
        payload = dict(data)
        payload["next_tasks"] = next_tasks
        return cls(**payload)


@dataclass
class ApprovalRecord:
    approval_id: str
    scope: str
    status: str
    created_at_iso: str
    requested_by_agent: str
    task_id: str
    entity_refs: dict[str, str] = field(default_factory=dict)
    payload_ref: str = ""
    summary: str = ""
    proposed_task: dict[str, Any] = field(default_factory=dict)
    approved_by: str = ""
    resolved_at_iso: str = ""
    resolution_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRecord":
        return cls(**data)


@dataclass
class ProfileLease:
    profile_key: str
    capability: str
    profile_no: str
    task_id: str
    agent: str
    leased_at_iso: str
    released_at_iso: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileLease":
        return cls(**data)


@dataclass(frozen=True)
class TaskTypeContract:
    task_type: str
    assigned_agent: str
    description: str
    requires_browser: bool = False
    required_profile_capability: str = ""
    requires_human_approval: bool = False
    approval_scope: str = ""
    max_attempts: int = 1


@dataclass(frozen=True)
class RouteRule:
    task_type: str
    downstream_task_type: str
    mode: str = "single"
    when_output_equals: dict[str, str] = field(default_factory=dict)
    when_output_in: dict[str, list[str]] = field(default_factory=dict)
    requires_approval: bool = False
    approval_scope: str = ""


@dataclass(frozen=True)
class ProfilePoolEntry:
    profile_key: str
    profile_no: str
    capability: str
    exclusive: bool = True
    managed_by: str = ""
    notes: str = ""
