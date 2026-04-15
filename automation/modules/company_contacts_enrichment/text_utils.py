from __future__ import annotations

import ctypes
import os
import re
import sys
from pathlib import Path

import yaml

MOJIBAKE_RE = re.compile(r"(?:Р[А-Яа-яЁёA-Za-z]|С[А-Яа-яЁёA-Za-z]|вЂ|Ђ|Ѓ)")


def repair_mojibake_text(value: str) -> str:
    text = str(value or "")
    if not text or not MOJIBAKE_RE.search(text):
        return text

    for encoding in ("cp1251", "latin1"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired and repaired != text and repaired.count("?") <= text.count("?"):
            return repaired
    return text


def repair_loaded_data(value):
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_loaded_data(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_loaded_data(item) for key, item in value.items()}
    return value


def load_yaml_utf8(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    return repair_loaded_data(data)


def _configure_windows_console_utf8() -> None:
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass


def configure_utf8_console() -> None:
    _configure_windows_console_utf8()
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if not stream or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
