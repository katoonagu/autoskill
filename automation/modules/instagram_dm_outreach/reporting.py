from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .state import InstagramDmOutreachState


@dataclass
class DmStatusRow:
    handle: str
    target_url: str
    profile_no: str
    status: str
    send_count: int
    reply_detected: bool
    last_sent_at_iso: str
    updated_at_iso: str
    detail: str
    last_message: str
    last_artifact_dir: str


def _targets_path(project_root: Path) -> Path:
    return project_root / "inputs" / "instagram_dm_outreach" / "targets.txt"


def _state_path(project_root: Path) -> Path:
    return project_root / "automation" / "state" / "instagram_dm_outreach_state.json"


def _status_json_path(project_root: Path) -> Path:
    return project_root / "output" / "instagram_dm_outreach" / "status_report.json"


def _status_md_path(project_root: Path) -> Path:
    return project_root / "output" / "instagram_dm_outreach" / "status_report.md"


def _load_targets(path: Path) -> list[str]:
    if not path.exists():
        return []
    targets: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        targets.append(value.split()[0].strip())
    return targets


def _handle_from_url(url: str) -> str:
    text = str(url or "").strip().rstrip("/")
    if "instagram.com/" not in text.lower():
        return text
    return text.rsplit("/", 1)[-1].lstrip("@")


def _rows_from_state(state: InstagramDmOutreachState, targets: Iterable[str]) -> list[DmStatusRow]:
    rows: dict[str, DmStatusRow] = {}

    for target in targets:
        handle = _handle_from_url(target)
        rows[handle] = DmStatusRow(
            handle=handle,
            target_url=target,
            profile_no="333",
            status="ready_to_send",
            send_count=0,
            reply_detected=False,
            last_sent_at_iso="",
            updated_at_iso="",
            detail="Цель ещё не проверялась.",
            last_message="",
            last_artifact_dir="",
        )

    for handle, entries in state.sent_messages.items():
        if not entries:
            continue
        latest = entries[-1]
        target_url = str(latest.get("target_url") or rows.get(handle, DmStatusRow(handle, "", "333", "", 0, False, "", "", "", "", "")).target_url)
        rows[handle] = DmStatusRow(
            handle=handle,
            target_url=target_url,
            profile_no=str(latest.get("profile_no") or "333"),
            status="thread_found_sent_only",
            send_count=len(entries),
            reply_detected=False,
            last_sent_at_iso=str(latest.get("sent_at_iso") or ""),
            updated_at_iso=str(state.last_audit_by_handle.get(handle, {}).get("updated_at_iso") or ""),
            detail="Есть локальная запись об отправке DM." if len(entries) == 1 else "Есть несколько локальных отправок DM.",
            last_message=str(latest.get("message") or ""),
            last_artifact_dir=str(latest.get("artifact_dir") or ""),
        )

    for handle, payload in state.last_audit_by_handle.items():
        row = rows.get(handle)
        if row is None:
            row = DmStatusRow(
                handle=handle,
                target_url=str(payload.get("target_url") or ""),
                profile_no="333",
                status="ready_to_send",
                send_count=0,
                reply_detected=False,
                last_sent_at_iso="",
                updated_at_iso="",
                detail="",
                last_message="",
                last_artifact_dir="",
            )
            rows[handle] = row
        row.status = str(payload.get("status") or row.status or "ready_to_send")
        row.reply_detected = bool(payload.get("reply_detected") or row.reply_detected)
        row.updated_at_iso = str(payload.get("updated_at_iso") or row.updated_at_iso)
        row.detail = str(payload.get("detail") or row.detail)
        row.target_url = str(payload.get("target_url") or row.target_url)
        row.send_count = max(row.send_count, int(payload.get("send_count") or row.send_count))
        row.last_sent_at_iso = str(payload.get("last_sent_at_iso") or row.last_sent_at_iso)
        row.last_artifact_dir = str(payload.get("last_artifact_dir") or row.last_artifact_dir)

    return sorted(rows.values(), key=lambda item: (item.handle.lower(), item.target_url))


def load_instagram_dm_status_rows(project_root: Path) -> list[DmStatusRow]:
    state = InstagramDmOutreachState.load(_state_path(project_root))
    targets = _load_targets(_targets_path(project_root))
    return _rows_from_state(state, targets)


def _write_json(path: Path, rows: list[DmStatusRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rows": [row.__dict__ for row in rows]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, rows: list[DmStatusRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Instagram DM Status",
        "",
        "| Handle | Status | Sends | Reply | Last Sent | Target |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row.handle}` | `{row.status}` | {row.send_count} | {'yes' if row.reply_detected else 'no'} | {row.last_sent_at_iso or '-'} | {row.target_url or '-'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _refresh_common_workbook(project_root: Path) -> None:
    try:
        from automation.modules.mail_outreach import build_contact_registry, write_mail_outreach_outputs
        from automation.modules.mail_outreach.state import AuditRecord
    except Exception:
        return
    audit_path = project_root / "output" / "mail_outreach" / "inbox_audit.json"
    raw_audits = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else []
    audits = [AuditRecord(**item) for item in raw_audits]
    registry = build_contact_registry(project_root)
    write_mail_outreach_outputs(project_root, registry, audits)


def write_instagram_dm_status_report(project_root: Path) -> dict:
    rows = load_instagram_dm_status_rows(project_root)
    _write_json(_status_json_path(project_root), rows)
    _write_md(_status_md_path(project_root), rows)
    _refresh_common_workbook(project_root)
    return {
        "rows": len(rows),
        "json_path": str(_status_json_path(project_root)),
        "md_path": str(_status_md_path(project_root)),
        "common_xlsx_path": str(project_root / "output" / "mail_outreach" / "tables" / "mail_outreach_common.xlsx"),
    }
