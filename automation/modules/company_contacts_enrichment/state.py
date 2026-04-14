from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class CompanyEnrichmentState:
    """Tracks enrichment progress across all target companies."""

    completed_companies: list[str] = field(default_factory=list)
    in_progress: str = ""
    failed_companies: dict[str, str] = field(default_factory=dict)  # slug -> error
    step_results: dict[str, dict[str, str]] = field(default_factory=dict)  # slug -> {step_N: status}

    @classmethod
    def load(cls, path: Path) -> "CompanyEnrichmentState":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                completed_companies=list(data.get("completed_companies") or []),
                in_progress=str(data.get("in_progress") or ""),
                failed_companies=dict(data.get("failed_companies") or {}),
                step_results=dict(data.get("step_results") or {}),
            )
        except Exception:
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "completed_companies": self.completed_companies,
            "in_progress": self.in_progress,
            "failed_companies": self.failed_companies,
            "step_results": self.step_results,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark_step_done(self, slug: str, step: int) -> None:
        if slug not in self.step_results:
            self.step_results[slug] = {}
        self.step_results[slug][f"step_{step}"] = "completed"

    def mark_step_failed(self, slug: str, step: int, error: str) -> None:
        if slug not in self.step_results:
            self.step_results[slug] = {}
        self.step_results[slug][f"step_{step}"] = f"failed: {error}"

    def is_completed(self, slug: str) -> bool:
        return slug in self.completed_companies

    def mark_completed(self, slug: str) -> None:
        if slug not in self.completed_companies:
            self.completed_companies.append(slug)
        if self.in_progress == slug:
            self.in_progress = ""
