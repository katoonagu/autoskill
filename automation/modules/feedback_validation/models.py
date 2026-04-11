from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationTask:
    brand_handle: str
    reason: str
    priority: str = "medium"


@dataclass
class ValidationFinding:
    brand_handle: str
    finding_type: str = ""
    confidence: str = ""
    summary: str = ""
    evidence_links: list[str] = field(default_factory=list)
