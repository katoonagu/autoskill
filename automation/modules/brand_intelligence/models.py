from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BrandIntelTask:
    brand_handle: str
    brand_url: str = ""
    source_blogger_handle: str = ""
    source_post_url: str = ""


@dataclass
class BrandIntelScore:
    brand_handle: str
    reputation_score: float = 0.0
    fit_score: float = 0.0
    risk_score: float = 0.0
    tone: str = ""
    niche: str = ""
    geo: str = ""
    price_segment: str = ""
    notes: list[str] = field(default_factory=list)
