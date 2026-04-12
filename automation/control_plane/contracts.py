from __future__ import annotations

from pathlib import Path

import yaml

from .models import ProfilePoolEntry, RouteRule, TaskTypeContract


def _contracts_root(project_root: Path) -> Path:
    return project_root / "automation" / "agents" / "contracts"


def load_task_type_contracts(project_root: Path) -> dict[str, TaskTypeContract]:
    path = _contracts_root(project_root) / "task_types.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    contracts: dict[str, TaskTypeContract] = {}
    for task_type, raw in (payload.get("task_types") or {}).items():
        contracts[task_type] = TaskTypeContract(
            task_type=task_type,
            assigned_agent=str(raw.get("assigned_agent") or ""),
            description=str(raw.get("description") or ""),
            requires_browser=bool(raw.get("requires_browser", False)),
            required_profile_capability=str(raw.get("required_profile_capability") or ""),
            requires_human_approval=bool(raw.get("requires_human_approval", False)),
            approval_scope=str(raw.get("approval_scope") or ""),
            max_attempts=int(raw.get("max_attempts", 1) or 1),
        )
    return contracts


def load_routing_rules(project_root: Path) -> dict[str, list[RouteRule]]:
    path = _contracts_root(project_root) / "routing_rules.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    routes: dict[str, list[RouteRule]] = {}
    for task_type, raw in (payload.get("routes") or {}).items():
        rules: list[RouteRule] = []
        for item in (raw.get("on_completed") or []):
            rules.append(
                RouteRule(
                    task_type=task_type,
                    downstream_task_type=str(item.get("task_type") or ""),
                    mode=str(item.get("mode") or "single"),
                    when_output_equals={
                        str(key): str(value)
                        for key, value in (item.get("when_output_equals") or {}).items()
                    },
                    when_output_in={
                        str(key): [str(candidate) for candidate in value]
                        for key, value in (item.get("when_output_in") or {}).items()
                    },
                    requires_approval=bool(item.get("requires_approval", False)),
                    approval_scope=str(item.get("approval_scope") or ""),
                )
            )
        routes[task_type] = rules
    return routes


def load_agent_registry(project_root: Path) -> dict:
    path = project_root / "automation" / "agents" / "registry.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_profile_pool(project_root: Path) -> dict[str, ProfilePoolEntry]:
    path = project_root / "automation" / "agents" / "profile_pool.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles: dict[str, ProfilePoolEntry] = {}
    for profile_key, raw in (payload.get("profiles") or {}).items():
        profiles[profile_key] = ProfilePoolEntry(
            profile_key=profile_key,
            profile_no=str(raw.get("profile_no") or ""),
            capability=str(raw.get("capability") or ""),
            exclusive=bool(raw.get("exclusive", True)),
            managed_by=str(raw.get("managed_by") or ""),
            notes=str(raw.get("notes") or ""),
        )
    return profiles
