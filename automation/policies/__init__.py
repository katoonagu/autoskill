from __future__ import annotations

from pathlib import Path

import yaml


def load_farida_policy(project_root: Path) -> dict:
    path = project_root / "automation" / "policies" / "farida_shirinova.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload
