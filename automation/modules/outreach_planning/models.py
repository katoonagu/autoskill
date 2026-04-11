from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OutreachPlanningTask:
    brand_handle: str
    blogger_handle: str
    preferred_channels: list[str] = field(default_factory=list)


@dataclass
class OutreachDecision:
    brand_handle: str
    blogger_handle: str
    should_contact: bool = False
    chosen_channel: str = ""
    angle: str = ""
    rationale: str = ""
