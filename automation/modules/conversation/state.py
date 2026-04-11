from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json


@dataclass
class ConversationState:
    current_conversation_key: str = ""
    completed_conversation_keys: list[str] = field(default_factory=list)
    threads: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "ConversationState":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
