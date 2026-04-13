from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import capture_screenshot, connect_profile
from automation.config import AdsPowerSettings, InstagramDmSettings
from automation.control_plane.storage import utcnow_iso

from .reporting import write_instagram_dm_status_report
from .state import InstagramDmAuditRecord, InstagramDmOutreachState


DM_STATUS_READY = "ready_to_send"
DM_STATUS_SENT = "thread_found_sent_only"
DM_STATUS_REPLY = "reply_detected"
_RNG = random.Random()
_DM_SETTINGS: InstagramDmSettings | None = None


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _sanitize_instagram_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("Instagram target URL is required")
    if not text.startswith("http"):
        text = "https://" + text.lstrip("/")
    if "instagram.com" not in text.lower():
        raise RuntimeError(f"Unsupported Instagram URL: {text}")
    return text


def _extract_handle(url: str) -> str:
    match = re.search(r"instagram\.com/([^/?#]+)/?", url, re.IGNORECASE)
    return match.group(1).strip().lstrip("@") if match else ""


def _state_path(project_root: Path) -> Path:
    return project_root / "automation" / "state" / "instagram_dm_outreach_state.json"


def _send_log_path(project_root: Path) -> Path:
    return project_root / "output" / "instagram_dm_outreach" / "send_log.jsonl"


def _targets_path(project_root: Path) -> Path:
    return project_root / "inputs" / "instagram_dm_outreach" / "targets.txt"


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_targets(project_root: Path) -> list[dict]:
    path = _targets_path(project_root)
    if not path.exists():
        return []
    items: list[dict] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        url = _sanitize_instagram_url(raw.split()[0].strip())
        handle = _extract_handle(url)
        if not handle or handle in seen:
            continue
        seen.add(handle)
        items.append({"handle": handle, "target_url": url})
    return items


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


async def _human_pause(page, base_ms: int, jitter_ms: int = 120) -> None:
    effective_jitter = jitter_ms if _DM_SETTINGS is None else _DM_SETTINGS.jitter_ms
    await page.wait_for_timeout(max(0, base_ms + _RNG.randint(0, effective_jitter)))


async def _move_mouse_to_locator(page, locator) -> None:
    if _DM_SETTINGS is not None and not _DM_SETTINGS.use_mouse_moves:
        return
    box = await locator.bounding_box()
    if not box:
        return
    target_x = box["x"] + (box["width"] / 2)
    target_y = box["y"] + (box["height"] / 2)
    current_x, current_y = await page.evaluate("() => [window.innerWidth / 2, 120]")
    mid_x = (current_x + target_x) / 2 + _RNG.uniform(-20, 20)
    mid_y = (current_y + target_y) / 2 + _RNG.uniform(-16, 16)
    await page.mouse.move(current_x, current_y, steps=4)
    await page.mouse.move(mid_x, mid_y, steps=6)
    await page.mouse.move(target_x, target_y, steps=10)


def build_test_dm_message() -> str:
    return (
        "Здравствуйте! Я представляю Farida Shirinova. "
        "Хотел бы кратко обсудить рекламное сотрудничество. "
        "Если Вам интересно, могу отправить статистику и 2-3 идеи интеграции."
    )


async def _dismiss_common_popups(page) -> None:
    labels = ["Not Now", "Не сейчас", "Close", "Закрыть", "Later", "Позже"]
    for label in labels:
        try:
            button = page.get_by_role("button", name=re.compile(rf"^{re.escape(label)}$", re.I)).first
            if await button.count() > 0:
                await button.click(timeout=1500)
                await page.wait_for_timeout(500)
        except Exception:
            continue


async def _wait_for_dm_composer(page, timeout_ms: int = 30000) -> None:
    selector = (
        "div[role='textbox'][contenteditable='true'][aria-placeholder='Message...'], "
        "div[role='textbox'][contenteditable='true'][aria-placeholder='Сообщение...'], "
        "div[role='textbox'][contenteditable='true'][aria-label='Message'], "
        "div[role='textbox'][contenteditable='true'][aria-label='Сообщение'], "
        "div[role='textbox'][contenteditable='true'][aria-describedby='Message'], "
        "div[role='textbox'][contenteditable='true'][aria-describedby='Сообщение'], "
        "div[role='textbox'][contenteditable='true']"
    )
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        if await page.locator(selector).count():
            return
        await page.wait_for_timeout(1000)
    raise RuntimeError("Instagram DM composer did not appear after opening the thread")


async def _focus_dm_composer(page) -> None:
    focused = await page.evaluate(
        """
        () => {
          const candidates = Array.from(document.querySelectorAll("div[role='textbox'][contenteditable='true']"));
          const target = candidates.find((el) => {
            const label = (el.getAttribute('aria-label') || '').toLowerCase();
            const placeholder = (el.getAttribute('aria-placeholder') || '').toLowerCase();
            const described = (el.getAttribute('aria-describedby') || '').toLowerCase();
            return (
              label.includes('message') ||
              label.includes('сообщение') ||
              placeholder.includes('message') ||
              placeholder.includes('сообщение') ||
              described.includes('message') ||
              described.includes('сообщение')
            );
          }) || candidates[0];
          if (!target) {
            return false;
          }
          target.focus();
          const range = document.createRange();
          range.selectNodeContents(target);
          range.collapse(false);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          return true;
        }
        """
    )
    if not focused:
        raise RuntimeError("Failed to focus Instagram DM composer")


async def _extract_thread_snapshot(page) -> dict:
    return await page.evaluate(
        """
        () => {
          const composer = Array.from(document.querySelectorAll("div[role='textbox'][contenteditable='true']")).find((el) => {
            const label = (el.getAttribute('aria-label') || '').toLowerCase();
            const placeholder = (el.getAttribute('aria-placeholder') || '').toLowerCase();
            const described = (el.getAttribute('aria-describedby') || '').toLowerCase();
            return (
              label.includes('message') ||
              label.includes('сообщение') ||
              placeholder.includes('message') ||
              placeholder.includes('сообщение') ||
              described.includes('message') ||
              described.includes('сообщение')
            );
          });
          let root = composer;
          let best = composer;
          while (root && root.parentElement) {
            root = root.parentElement;
            const rect = root.getBoundingClientRect();
            if (rect.width >= 260 && rect.height >= 300) {
              best = root;
              break;
            }
          }
          const text = (best?.innerText || composer?.innerText || "").trim();
          const visibleTextboxes = Array.from(document.querySelectorAll("div[role='textbox'][contenteditable='true']")).length;
          return { text, visibleTextboxes };
        }
        """
    )


def _extract_candidate_lines(thread_text: str, handle: str) -> list[str]:
    noise = {
        "",
        "message...",
        "сообщение...",
        "view profile",
        "instagram",
        handle.lower(),
    }
    lines: list[str] = []
    for line in str(thread_text or "").splitlines():
        clean = re.sub(r"\s+", " ", line.strip())
        lowered = clean.lower()
        if not clean or lowered in noise:
            continue
        if lowered.startswith("view profile"):
            continue
        if lowered in {"message", "сообщение"}:
            continue
        lines.append(clean)
    return lines


def _classify_audit_record(
    *,
    handle: str,
    target_url: str,
    thread_text: str,
    send_entries: list[dict],
    artifact_dir: str = "",
) -> InstagramDmAuditRecord:
    send_count = len(send_entries)
    last_sent_at_iso = str(send_entries[-1].get("sent_at_iso") or "") if send_entries else ""
    sent_messages = [_normalize_text(item.get("message") or "") for item in send_entries]
    candidate_lines = _extract_candidate_lines(thread_text, handle)
    unmatched_lines: list[str] = []
    for line in candidate_lines:
        normalized = _normalize_text(line)
        if not normalized:
            continue
        if sent_messages and any(normalized in sent or sent in normalized for sent in sent_messages if sent):
            continue
        unmatched_lines.append(line)

    if unmatched_lines and send_count > 0:
        status = DM_STATUS_REPLY
        detail = "В треде есть текст, который не совпадает с нашими сохранёнными исходящими сообщениями."
        reply_detected = True
    elif send_count > 0 or candidate_lines:
        status = DM_STATUS_SENT
        detail = "Тред найден, но явного нового ответа не обнаружено."
        reply_detected = False
    else:
        status = DM_STATUS_READY
        detail = "Тред не найден, профиль выглядит как новый для отправки."
        reply_detected = False

    return InstagramDmAuditRecord(
        handle=handle,
        target_url=target_url,
        status=status,
        detail=detail,
        send_count=send_count,
        reply_detected=reply_detected,
        updated_at_iso=utcnow_iso(),
        last_sent_at_iso=last_sent_at_iso,
        last_artifact_dir=artifact_dir,
    )


async def _open_session(project_root: Path, *, label: str, profile_no: str):
    artifacts, logger = setup_run_artifacts(project_root, label)
    settings = AdsPowerSettings.from_project_root(project_root)
    client = AdsPowerClient(
        AdsPowerSettings(base_url=settings.base_url, api_key=settings.api_key, profile_no=profile_no)
    )
    started = client.start_profile(profile_no=profile_no, last_opened_tabs=False)
    playwright = await async_playwright().start()
    browser, context, connected_page = await connect_profile(playwright, started.ws_puppeteer, logger)
    page = connected_page if connected_page else await context.new_page()
    await page.bring_to_front()
    for extra_page in list(context.pages)[1:]:
        try:
            await extra_page.close()
        except Exception:
            pass
    return client, playwright, browser, page, artifacts, logger


async def _close_session(client, playwright, browser, profile_no: str) -> None:
    if browser is not None:
        try:
            await browser.close()
        except Exception:
            pass
    if playwright is not None:
        try:
            await playwright.stop()
        except Exception:
            pass
    try:
        client.stop_profile(profile_no=profile_no)
    except Exception:
        pass


async def _open_dm_thread(page, *, target_url: str, handle: str, logger, open_shot: Path | None = None) -> None:
    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        logger.info("Instagram profile did not reach networkidle")
    await _dismiss_common_popups(page)
    logger.info("Opening Instagram DM thread for @%s", handle or target_url)
    message_button = page.locator("main div[role='button']").filter(
        has_text=re.compile(r"^(Message|Сообщение|Написать)$", re.I)
    ).first
    if await message_button.count() == 0:
        message_button = page.locator("div[role='button']").filter(
            has_text=re.compile(r"^(Message|Сообщение|Написать)$", re.I)
        ).first
    await message_button.scroll_into_view_if_needed(timeout=5000)
    await _human_pause(page, 350, 180)
    await _move_mouse_to_locator(page, message_button)
    await _human_pause(page, 180, 120)
    await message_button.click(timeout=20000, force=True)
    await _human_pause(page, 2200, 900)
    if open_shot is not None:
        await capture_screenshot(page, open_shot, logger)
    await _dismiss_common_popups(page)


async def _send_in_open_thread(page, *, message: str, logger, after_shot: Path | None = None) -> None:
    logger.info("Waiting for Instagram DM composer")
    await _wait_for_dm_composer(page, timeout_ms=30000)
    await _focus_dm_composer(page)
    composer = page.locator(
        "div[role='textbox'][contenteditable='true'][aria-placeholder='Message...'], "
        "div[role='textbox'][contenteditable='true'][aria-placeholder='Сообщение...'], "
        "div[role='textbox'][contenteditable='true'][aria-label='Message'], "
        "div[role='textbox'][contenteditable='true'][aria-label='Сообщение'], "
        "div[role='textbox'][contenteditable='true'][aria-describedby='Message'], "
        "div[role='textbox'][contenteditable='true'][aria-describedby='Сообщение'], "
        "div[role='textbox'][contenteditable='true']"
    ).first
    await _move_mouse_to_locator(page, composer)
    await _human_pause(page, 150, 120)
    await composer.click(timeout=10000)
    await _human_pause(page, 180, 120)
    typing_delay_ms = 300 if _DM_SETTINGS is None else _DM_SETTINGS.typing_delay_ms
    await page.keyboard.type(message, delay=typing_delay_ms)
    await _human_pause(page, 280, 160)
    send_button = page.get_by_role("button", name=re.compile(r"^(Send|Отправить)$", re.I)).first
    if await send_button.count() > 0:
        await _move_mouse_to_locator(page, send_button)
        await _human_pause(page, 140, 100)
        await send_button.click(timeout=10000)
    else:
        await page.keyboard.press("Enter")
    await _human_pause(page, 1400, 500)
    if after_shot is not None:
        await capture_screenshot(page, after_shot, logger)


def _record_send(project_root: Path, *, handle: str, target_url: str, profile_no: str, message: str, artifacts) -> dict:
    payload = {
        "target_url": target_url,
        "handle": handle,
        "profile_no": profile_no,
        "message": message,
        "sent_at_iso": utcnow_iso(),
        "artifact_dir": str(artifacts.run_dir),
        "log_path": str(artifacts.log_path),
        "screenshot_before": str(artifacts.screenshots_dir / "before_send.png"),
        "screenshot_after_open": str(artifacts.screenshots_dir / "after_open_thread.png"),
        "screenshot_after": str(artifacts.screenshots_dir / "after_send.png"),
    }
    _append_jsonl(_send_log_path(project_root), payload)
    state = InstagramDmOutreachState.load(_state_path(project_root))
    state.sent_messages.setdefault(handle or target_url, []).append(payload)
    state.last_send_at_iso = payload["sent_at_iso"]
    state.save(_state_path(project_root))
    return payload


async def send_instagram_dm_message(
    project_root: Path,
    *,
    target_url: str,
    message: str,
    profile_no: str = "333",
) -> dict:
    global _DM_SETTINGS
    normalized_url = _sanitize_instagram_url(target_url)
    handle = _extract_handle(normalized_url)
    _DM_SETTINGS = InstagramDmSettings.from_project_root(project_root)
    client, playwright, browser, page, artifacts, logger = await _open_session(
        project_root, label=f"instagram_dm_send_{_slug(handle or normalized_url)}", profile_no=profile_no
    )
    try:
        await capture_screenshot(page, artifacts.screenshots_dir / "before_send.png", logger)
        await _open_dm_thread(
            page,
            target_url=normalized_url,
            handle=handle,
            logger=logger,
            open_shot=artifacts.screenshots_dir / "after_open_thread.png",
        )
        await _send_in_open_thread(
            page,
            message=message,
            logger=logger,
            after_shot=artifacts.screenshots_dir / "after_send.png",
        )
    finally:
        await _close_session(client, playwright, browser, profile_no)

    payload = _record_send(
        project_root,
        handle=handle,
        target_url=normalized_url,
        profile_no=profile_no,
        message=message,
        artifacts=artifacts,
    )
    write_instagram_dm_status_report(project_root)
    return payload


async def audit_instagram_dm_targets(project_root: Path, *, limit: int | None = None, profile_no: str = "333") -> list[InstagramDmAuditRecord]:
    global _DM_SETTINGS
    targets = _load_targets(project_root)
    if limit:
        targets = targets[:limit]
    _DM_SETTINGS = InstagramDmSettings.from_project_root(project_root)
    state = InstagramDmOutreachState.load(_state_path(project_root))
    client, playwright, browser, page, artifacts, logger = await _open_session(
        project_root, label="instagram_dm_audit", profile_no=profile_no
    )
    audits: list[InstagramDmAuditRecord] = []
    try:
        for item in targets:
            handle = item["handle"]
            target_url = item["target_url"]
            shot = artifacts.screenshots_dir / f"{_slug(handle)}_thread.png"
            try:
                await _open_dm_thread(page, target_url=target_url, handle=handle, logger=logger, open_shot=shot)
                snapshot = await _extract_thread_snapshot(page)
                audit = _classify_audit_record(
                    handle=handle,
                    target_url=target_url,
                    thread_text=str(snapshot.get("text") or ""),
                    send_entries=list(state.sent_messages.get(handle, [])),
                    artifact_dir=str(artifacts.run_dir),
                )
            except Exception as exc:
                audit = InstagramDmAuditRecord(
                    handle=handle,
                    target_url=target_url,
                    status=DM_STATUS_READY,
                    detail=f"Audit failed: {exc}",
                    send_count=len(state.sent_messages.get(handle, [])),
                    reply_detected=False,
                    updated_at_iso=utcnow_iso(),
                    last_sent_at_iso=str((state.sent_messages.get(handle, [{}])[-1] or {}).get("sent_at_iso") or ""),
                    last_artifact_dir=str(artifacts.run_dir),
                )
            audits.append(audit)
            state.last_audit_by_handle[handle] = audit.to_dict()
    finally:
        state.last_audit_at_iso = utcnow_iso()
        state.save(_state_path(project_root))
        await _close_session(client, playwright, browser, profile_no)

    write_instagram_dm_status_report(project_root)
    return audits


async def run_instagram_dm_cycle(
    project_root: Path,
    *,
    send_ready: bool,
    limit: int = 5,
    profile_no: str = "333",
    message: str = "",
) -> dict:
    global _DM_SETTINGS
    targets = _load_targets(project_root)
    _DM_SETTINGS = InstagramDmSettings.from_project_root(project_root)
    state = InstagramDmOutreachState.load(_state_path(project_root))
    client, playwright, browser, page, artifacts, logger = await _open_session(
        project_root, label="instagram_dm_cycle", profile_no=profile_no
    )
    audits: list[InstagramDmAuditRecord] = []
    sent_count = 0
    default_message = message.strip() or build_test_dm_message()
    try:
        for item in targets:
            handle = item["handle"]
            target_url = item["target_url"]
            shot = artifacts.screenshots_dir / f"{_slug(handle)}_audit.png"
            try:
                await _open_dm_thread(page, target_url=target_url, handle=handle, logger=logger, open_shot=shot)
                snapshot = await _extract_thread_snapshot(page)
                audit = _classify_audit_record(
                    handle=handle,
                    target_url=target_url,
                    thread_text=str(snapshot.get("text") or ""),
                    send_entries=list(state.sent_messages.get(handle, [])),
                    artifact_dir=str(artifacts.run_dir),
                )
            except Exception as exc:
                audit = InstagramDmAuditRecord(
                    handle=handle,
                    target_url=target_url,
                    status=DM_STATUS_READY,
                    detail=f"Audit failed: {exc}",
                    send_count=len(state.sent_messages.get(handle, [])),
                    reply_detected=False,
                    updated_at_iso=utcnow_iso(),
                    last_sent_at_iso=str((state.sent_messages.get(handle, [{}])[-1] or {}).get("sent_at_iso") or ""),
                    last_artifact_dir=str(artifacts.run_dir),
                )
            audits.append(audit)
            state.last_audit_by_handle[handle] = audit.to_dict()

        if send_ready:
            ready_items = [item for item in audits if item.status == DM_STATUS_READY][:limit]
            target_map = {item["handle"]: item["target_url"] for item in targets}
            for audit in ready_items:
                handle = audit.handle
                target_url = target_map.get(handle)
                if not target_url:
                    continue
                before_shot = artifacts.screenshots_dir / f"{_slug(handle)}_before_send.png"
                after_open_shot = artifacts.screenshots_dir / f"{_slug(handle)}_after_open.png"
                after_send_shot = artifacts.screenshots_dir / f"{_slug(handle)}_after_send.png"
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    logger.info("Instagram profile did not reach networkidle")
                await capture_screenshot(page, before_shot, logger)
                await _open_dm_thread(page, target_url=target_url, handle=handle, logger=logger, open_shot=after_open_shot)
                await _send_in_open_thread(page, message=default_message, logger=logger, after_shot=after_send_shot)
                payload = {
                    "target_url": target_url,
                    "handle": handle,
                    "profile_no": profile_no,
                    "message": default_message,
                    "sent_at_iso": utcnow_iso(),
                    "artifact_dir": str(artifacts.run_dir),
                    "log_path": str(artifacts.log_path),
                    "screenshot_before": str(before_shot),
                    "screenshot_after_open": str(after_open_shot),
                    "screenshot_after": str(after_send_shot),
                }
                _append_jsonl(_send_log_path(project_root), payload)
                state.sent_messages.setdefault(handle, []).append(payload)
                state.last_send_at_iso = payload["sent_at_iso"]
                sent_count += 1

            # Re-audit after sending within the same session.
            audits = []
            for item in targets:
                handle = item["handle"]
                target_url = item["target_url"]
                shot = artifacts.screenshots_dir / f"{_slug(handle)}_post_audit.png"
                try:
                    await _open_dm_thread(page, target_url=target_url, handle=handle, logger=logger, open_shot=shot)
                    snapshot = await _extract_thread_snapshot(page)
                    audit = _classify_audit_record(
                        handle=handle,
                        target_url=target_url,
                        thread_text=str(snapshot.get("text") or ""),
                        send_entries=list(state.sent_messages.get(handle, [])),
                        artifact_dir=str(artifacts.run_dir),
                    )
                except Exception as exc:
                    audit = InstagramDmAuditRecord(
                        handle=handle,
                        target_url=target_url,
                        status=DM_STATUS_READY,
                        detail=f"Post-send audit failed: {exc}",
                        send_count=len(state.sent_messages.get(handle, [])),
                        reply_detected=False,
                        updated_at_iso=utcnow_iso(),
                        last_sent_at_iso=str((state.sent_messages.get(handle, [{}])[-1] or {}).get("sent_at_iso") or ""),
                        last_artifact_dir=str(artifacts.run_dir),
                    )
                audits.append(audit)
                state.last_audit_by_handle[handle] = audit.to_dict()
    finally:
        state.last_audit_at_iso = utcnow_iso()
        state.save(_state_path(project_root))
        await _close_session(client, playwright, browser, profile_no)

    write_instagram_dm_status_report(project_root)
    return {"audits": [item.to_dict() for item in audits], "sent_count": sent_count, "artifact_dir": str(artifacts.run_dir)}
