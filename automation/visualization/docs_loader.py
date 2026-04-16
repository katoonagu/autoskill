from __future__ import annotations

from pathlib import Path

from .utils import safe_read_text


def docs_root(project_root: Path) -> Path:
    return project_root / "docs" / "agent_canvas" / "nodes"


def load_node_doc(project_root: Path, node_id: str) -> str:
    path = docs_root(project_root) / f"{node_id}.md"
    content = safe_read_text(path).strip()
    if content:
        return content
    title = node_id.replace(".", " ").replace("_", " ").title()
    return f"# {title}\n\nNo curated node note has been written yet.\n"
