from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BrowserSubagentSpec:
    name: str
    role: str
    profile_no: str
    start_url: str
    purpose: str
    enabled: bool = True
    keep_browser_open: bool = True
    allowed_channels: list[str] = field(default_factory=list)
    writes_messages: bool = False
    human_approval_required: bool = True
    managed_by_module: str = ""
    memory_workspace: str = ""
    notes: str = ""


@dataclass
class BrowserSubagentState:
    agent_name: str = ""
    role: str = ""
    profile_no: str = ""
    purpose: str = ""
    status: str = "idle"
    current_url: str = ""
    last_started_at_iso: str = ""
    last_connected_at_iso: str = ""
    last_completed_at_iso: str = ""
    last_artifact_dir: str = ""
    last_log_path: str = ""
    last_screenshot_path: str = ""
    allowed_channels: list[str] = field(default_factory=list)
    writes_messages: bool = False
    human_approval_required: bool = True
    managed_by_module: str = ""
    memory_workspace: str = ""
