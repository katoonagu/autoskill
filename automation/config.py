from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _load_env_files(project_root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    values.update(_read_env_file(project_root / ".env"))
    values.update(_read_env_file(project_root / ".env.local"))
    return values


@dataclass(frozen=True)
class AdsPowerSettings:
    base_url: str
    api_key: str
    profile_no: str

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AdsPowerSettings":
        values = _load_env_files(project_root)
        base_url = os.environ.get("ADSPOWER_BASE_URL") or values.get("ADSPOWER_BASE_URL")
        api_key = os.environ.get("ADSPOWER_API_KEY") or values.get("ADSPOWER_API_KEY")
        profile_no = os.environ.get("ADSPOWER_PROFILE_NO") or values.get("ADSPOWER_PROFILE_NO")

        missing = [
            key
            for key, value in {
                "ADSPOWER_BASE_URL": base_url,
                "ADSPOWER_API_KEY": api_key,
                "ADSPOWER_PROFILE_NO": profile_no,
            }.items()
            if not value
        ]
        if missing:
            missing_str = ", ".join(missing)
            raise RuntimeError(f"Missing AdsPower configuration: {missing_str}")

        return cls(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            profile_no=profile_no,
        )


@dataclass(frozen=True)
class InstagramDmSettings:
    typing_delay_ms: int = 300
    jitter_ms: int = 120
    use_mouse_moves: bool = True

    @classmethod
    def from_project_root(cls, project_root: Path) -> "InstagramDmSettings":
        values = _load_env_files(project_root)
        typing_delay_raw = os.environ.get("INSTAGRAM_DM_TYPING_DELAY_MS") or values.get("INSTAGRAM_DM_TYPING_DELAY_MS")
        jitter_raw = os.environ.get("INSTAGRAM_DM_JITTER_MS") or values.get("INSTAGRAM_DM_JITTER_MS")
        use_mouse_moves_raw = os.environ.get("INSTAGRAM_DM_USE_MOUSE_MOVES") or values.get("INSTAGRAM_DM_USE_MOUSE_MOVES")

        typing_delay_ms = 300
        if typing_delay_raw:
            typing_delay_ms = max(0, int(typing_delay_raw))

        jitter_ms = 120
        if jitter_raw:
            jitter_ms = max(0, int(jitter_raw))

        use_mouse_moves = True
        if use_mouse_moves_raw:
            use_mouse_moves = str(use_mouse_moves_raw).strip().lower() not in {"0", "false", "no", "off"}

        return cls(
            typing_delay_ms=typing_delay_ms,
            jitter_ms=jitter_ms,
            use_mouse_moves=use_mouse_moves,
        )
