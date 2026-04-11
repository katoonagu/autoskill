from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .models import BrowserSubagentState


def load_subagent_state(path: Path) -> BrowserSubagentState:
    if not path.exists():
        return BrowserSubagentState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return BrowserSubagentState(**data)


def save_subagent_state(path: Path, state: BrowserSubagentState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
