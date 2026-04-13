from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json


@dataclass
class ContactRecord:
    contact_id: str
    email: str
    instagram_url: str = ""
    brand_handle: str = ""
    brand_name: str = ""
    source: str = ""
    source_details: list[str] = field(default_factory=list)
    notes: str = ""
    profile_url: str = ""
    primary_site_url: str = ""
    preferred_contact_channel: str = "email"
    dossier_json_path: str = ""
    dossier_md_path: str = ""
    brand_folder: str = ""
    brand_followers: int = 0
    brand_posts: int = 0
    brand_value_tier: str = ""
    is_ultra_premium_brand: bool = False
    special_handling: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditRecord:
    contact_id: str
    email: str
    brand_handle: str = ""
    brand_name: str = ""
    instagram_url: str = ""
    status: str = ""
    detail: str = ""
    query_url: str = ""
    result_count: int = 0
    unread_count: int = 0
    local_sent_count: int = 0
    body_preview: str = ""
    updated_at_iso: str = ""
    preferred_contact_channel: str = "email"
    is_ultra_premium_brand: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MailOutreachState:
    last_registry_built_at_iso: str = ""
    last_audit_at_iso: str = ""
    last_send_at_iso: str = ""
    sent_messages: dict[str, list[dict]] = field(default_factory=dict)
    last_audit_by_email: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "MailOutreachState":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
