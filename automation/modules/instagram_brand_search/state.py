from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json

from .models import BloggerCheckpoint


@dataclass
class InstagramBrandSearchState:
    current_blogger_url: str = ""
    current_post_url: str = ""
    current_post_date_iso: str = ""
    completed_bloggers: list[str] = field(default_factory=list)
    completed_following_expansions: list[str] = field(default_factory=list)
    checkpoints: dict[str, BloggerCheckpoint] = field(default_factory=dict)
    brand_records: dict[str, dict] = field(default_factory=dict)
    blogger_stats: dict[str, dict] = field(default_factory=dict)
    following_candidates: dict[str, dict] = field(default_factory=dict)
    following_progress: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "InstagramBrandSearchState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        checkpoints_raw = data.pop("checkpoints", {})
        state = cls(**data)
        state.checkpoints = {
            url: BloggerCheckpoint(**checkpoint)
            for url, checkpoint in checkpoints_raw.items()
        }
        return state

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def checkpoint_for(self, blogger_url: str) -> BloggerCheckpoint:
        checkpoint = self.checkpoints.get(blogger_url)
        if checkpoint is None:
            checkpoint = BloggerCheckpoint(profile_url=blogger_url)
            self.checkpoints[blogger_url] = checkpoint
        return checkpoint

    def mark_blogger_completed(self, blogger_url: str) -> None:
        if blogger_url not in self.completed_bloggers:
            self.completed_bloggers.append(blogger_url)
        if self.current_blogger_url == blogger_url:
            self.current_blogger_url = ""
        if self.current_post_url and self.checkpoints.get(blogger_url, BloggerCheckpoint(blogger_url)).current_post_url == self.current_post_url:
            self.current_post_url = ""
            self.current_post_date_iso = ""

    def mark_following_expansion_completed(self, blogger_url: str) -> None:
        if blogger_url not in self.completed_following_expansions:
            self.completed_following_expansions.append(blogger_url)

    def following_progress_for(self, blogger_url: str) -> dict:
        progress = self.following_progress.get(blogger_url)
        if progress is None:
            progress = {
                "discovered_handles": [],
                "inspected_handles": [],
                "qualified_handles": [],
                "last_processed_handle": "",
                "last_visible_handle": "",
                "target_qualified_accounts": 0,
                "list_exhausted": False,
            }
            self.following_progress[blogger_url] = progress
        return progress
