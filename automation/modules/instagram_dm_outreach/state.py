from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json


@dataclass
class InstagramDmAuditRecord:
    handle: str
    target_url: str = ""
    status: str = ""
    detail: str = ""
    send_count: int = 0
    reply_detected: bool = False
    updated_at_iso: str = ""
    last_sent_at_iso: str = ""
    last_artifact_dir: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InstagramDmOutreachState:
    last_send_at_iso: str = ""
    last_audit_at_iso: str = ""
    sent_messages: dict[str, list[dict]] = field(default_factory=dict)
    last_audit_by_handle: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "InstagramDmOutreachState":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
