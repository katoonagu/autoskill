from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    log_path: Path

    @property
    def screenshots_dir(self) -> Path:
        return self.run_dir / "screenshots"


def setup_run_artifacts(project_root: Path, label: str) -> tuple[RunArtifacts, logging.Logger]:
    run_dir = project_root / "output" / "playwright" / f"{_timestamp()}_{label}"
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"

    logger = logging.getLogger(f"automation.{label}.{_timestamp()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return RunArtifacts(run_dir=run_dir, log_path=log_path), logger

