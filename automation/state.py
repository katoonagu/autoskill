from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class GenaiproState:
    account_email: str = ""
    account_tier: str = ""
    account_row_text: str = ""
    project_name: str = ""
    project_url: str = ""
    project_id: str = ""
    current_reference: str = ""
    completed_references: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "GenaiproState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    def mark_completed(self, filename: str) -> None:
        if filename not in self.completed_references:
            self.completed_references.append(filename)
        if self.current_reference == filename:
            self.current_reference = ""

