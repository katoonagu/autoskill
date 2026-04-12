from __future__ import annotations

from dataclasses import asdict, dataclass, field
from dataclasses import fields as dataclass_fields
from pathlib import Path
import json


@dataclass
class BrandIntelligenceState:
    current_brand_handle: str = ""
    completed_brand_handles: list[str] = field(default_factory=list)
    evidence_bundles: dict[str, dict] = field(default_factory=dict)
    research_reports: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "BrandIntelligenceState":
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        allowed = {item.name for item in dataclass_fields(cls)}
        normalized = {key: value for key, value in payload.items() if key in allowed}
        return cls(**normalized)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
