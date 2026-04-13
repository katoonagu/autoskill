from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import capture_screenshot, connect_profile
from automation.config import AdsPowerSettings
from automation.control_plane.models import AgentTask, TaskResult
from automation.control_plane.storage import utcnow_iso
from automation.policies import load_farida_policy

from .state import ConversationState
from .style_policies import get_channel_style_policy


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip().lower()) or "unknown"


def _load_json(path_value: str) -> dict:
    path = Path(path_value)
    if not path.is_file():
        raise RuntimeError(f"Conversation input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_draft_body(draft_path: Path) -> str:
    text = draft_path.read_text(encoding="utf-8-sig")
    if "## Draft" not in text:
        return text.strip()
    block = text.split("## Draft", 1)[1]
    for marker in ("## Context", "## Why Now", "## Supporting Stats", "## Guardrails"):
        if marker in block:
            block = block.split(marker, 1)[0]
            break
    return block.strip()


def _format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _format_views_mln(value: int) -> str:
    return str(round(int(value) / 1_000_000, 1)).replace(".", ",")


def _build_offer_body(
    *,
    brand_label: str,
    channel: str,
    why_this_brand: str,
    policy: dict,
) -> str:
    channel_policy = get_channel_style_policy(channel)
    creator = dict(policy.get("creator") or {})
    metrics = dict(policy.get("audience_metrics") or {})
    cta_policy = dict(policy.get("cta_policy") or {})
    offer_strategy = dict(policy.get("offer_strategy") or {})

    creator_name = str(creator.get("name") or "Farida Shirinova")
    creator_handle = str(creator.get("handle") or "farida.shirinova").strip()

    followers = int(metrics.get("followers") or 0)
    reels_views_30d = int(metrics.get("reels_views_30d") or 0)
    women_share_percent = metrics.get("women_share_percent") or 0
    core_age_range = str(metrics.get("core_age_range") or "").strip()
    primary_geo = str(metrics.get("primary_geo") or "").strip()
    moscow_share_percent = metrics.get("moscow_share_percent") or 0
    recommendation_share_percent = str(metrics.get("recommendation_share_percent") or 0).replace(".", ",")
    strongest_value_prop = str(offer_strategy.get("strongest_value_prop") or "").strip()

    intro = (
        f"{channel_policy['salutation']} Меня зовут Владислав, я представляю {creator_name}. "
        f"Профиль блогера: @{creator_handle}. Предлагаю обсудить рекламную интеграцию для {brand_label}."
    )
    fit_line = f"Считаю, что {brand_label} хорошо подходит под такой формат сотрудничества." if why_this_brand.strip() else ""
    metrics_line = (
        f"Коротко по профилю: {_format_int(followers)} подписчиков, {_format_views_mln(reels_views_30d)} млн просмотров в Reels за последние 30 дней, "
        f"{recommendation_share_percent}% просмотров приходят из рекомендаций, {women_share_percent}% аудитории — женщины, "
        f"ядро аудитории — {core_age_range}, основная география — {primary_geo}"
        + (f" (Москва — {moscow_share_percent}%)." if moscow_share_percent else ".")
    )
    value_line = (
        "Для Вашего бренда это рабочий формат на узнаваемость, расширение касаний с женской аудиторией "
        "и имиджевое присутствие в сильном lifestyle-контенте."
    )
    if strongest_value_prop:
        value_line = f"{value_line} {strongest_value_prop}"
    close = str(cta_policy.get("preferred") or channel_policy["cta"]).strip()
    return " ".join(part for part in [intro, fit_line, metrics_line, value_line, close] if part)


async def _run_instagram_dm_send(
    project_root: Path,
    *,
    profile_no: str,
    target_url: str,
    draft_text: str,
    conversation_key: str,
) -> dict:
    artifacts, logger = setup_run_artifacts(project_root, f"conversation_send_{conversation_key}")
    settings = AdsPowerSettings.from_project_root(project_root)
    client = AdsPowerClient(
        AdsPowerSettings(
            base_url=settings.base_url,
            api_key=settings.api_key,
            profile_no=profile_no,
        )
    )
    started = client.start_profile(profile_no=profile_no, last_opened_tabs=False)
    screenshot_before = artifacts.screenshots_dir / "before_send.png"
    screenshot_after = artifacts.screenshots_dir / "after_send.png"
    browser = None

    try:
        async with async_playwright() as playwright:
            browser, context, connected_page = await connect_profile(playwright, started.ws_puppeteer, logger)
            page = connected_page if connected_page else await context.new_page()
            await page.bring_to_front()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                logger.info("Networkidle did not settle for %s", target_url)
            await capture_screenshot(page, screenshot_before, logger)

            message_button = page.get_by_role("button", name=re.compile(r"(message|сообщение|написать)", re.I)).first
            await message_button.click(timeout=15000)

            composer = page.locator("textarea").first
            if await composer.count() == 0:
                composer = page.locator("[contenteditable='true']").first
            await composer.click(timeout=15000)
            await page.keyboard.type(draft_text, delay=20)

            send_button = page.get_by_role("button", name=re.compile(r"(send|отправить)", re.I)).first
            if await send_button.count() > 0:
                await send_button.click(timeout=10000)
            else:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(1500)
            await capture_screenshot(page, screenshot_after, logger)
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception as exc:
                logger.warning("Failed to close browser after send: %s", exc)
        try:
            client.stop_profile(profile_no=profile_no)
        except Exception as exc:
            logger.warning("Failed to stop AdsPower profile %s after send: %s", profile_no, exc)

    return {
        "artifact_dir": str(artifacts.run_dir),
        "log_path": str(artifacts.log_path),
        "screenshot_before": str(screenshot_before),
        "screenshot_after": str(screenshot_after),
    }


def _prepare_draft(project_root: Path, task: AgentTask, *, write_wiki: bool) -> TaskResult:
    planning_payload = _load_json(str(task.inputs.get("decision_path", "")))
    brand_handle = str(planning_payload.get("brand_handle") or task.entity_refs.get("brand_handle") or "")
    blogger_handle = str(planning_payload.get("blogger_handle") or task.entity_refs.get("blogger_handle") or "")
    channel = str(planning_payload.get("chosen_channel") or "instagram_dm")
    snapshot = _load_json(str(task.inputs.get("brand_snapshot_path", "")))
    if str(planning_payload.get("recommended_action") or "") != "prepare_draft":
        raise RuntimeError("conversation.prepare_draft received a planning decision that is not outreach-ready")

    brand_label = str(snapshot.get("display_name") or f"@{brand_handle}")
    why_this_brand = str(planning_payload.get("why_this_brand") or "")
    why_now = str(planning_payload.get("why_now") or "")
    what_not_to_say = [str(item).strip() for item in (planning_payload.get("what_not_to_say") or []) if str(item).strip()]
    supporting_stats = dict(planning_payload.get("supporting_stats") or {})
    creator_policy = load_farida_policy(project_root)
    supporting_stat_lines = [f"- {key}: {value}" for key, value in supporting_stats.items()] or ["- Статистика пока не приложена."]
    guardrail_lines = [f"- {item}" for item in what_not_to_say] or ["- Не использовать непроверенные утверждения."]
    conversation_key = f"{_slug(brand_handle)}__{_slug(blogger_handle or 'unknown')}__{channel}"

    draft_dir = project_root / "output" / "conversation" / conversation_key
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "draft.md"
    status_path = draft_dir / "status.json"

    draft_lines = [
        f"# Draft @{brand_handle} -> @{blogger_handle or 'unknown'}",
        "",
        f"- Channel: {channel}",
        "",
        "## Draft",
        _build_offer_body(
            brand_label=brand_label,
            channel=channel,
            why_this_brand=why_this_brand,
            policy=creator_policy,
        ),
        "",
        "## Context",
        why_this_brand or "Контекст по бренду не был явно сформулирован.",
        "",
        "## Why Now",
        why_now or "Отдельный timing hook не сформулирован.",
        "",
        "## Supporting Stats",
        *supporting_stat_lines,
        "",
        "## Guardrails",
        *guardrail_lines,
        "- Требуется ручная проверка перед любой отправкой.",
        "- Генерация draft не отправляет сообщение автоматически.",
        "",
    ]
    draft_path.write_text("\n".join(draft_lines), encoding="utf-8-sig")

    status_payload = {
        "conversation_key": conversation_key,
        "status": "draft_ready",
        "channel": channel,
        "next_action": "approve_send",
        "draft_path": str(draft_path),
        "why_this_brand": why_this_brand,
        "why_now": why_now,
    }
    status_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    state_path = project_root / "automation" / "state" / "conversation_state.json"
    state = ConversationState.load(state_path)
    state.current_conversation_key = conversation_key
    state.threads[conversation_key] = {
        "channel": channel,
        "status": "draft_ready",
        "last_message_summary": "Draft generated from approved outreach plan.",
        "next_action": "approve_send",
        "draft_path": str(draft_path),
        "why_this_brand": why_this_brand,
        "why_now": why_now,
    }
    if conversation_key not in state.completed_conversation_keys:
        state.completed_conversation_keys.append(conversation_key)
    state.current_conversation_key = ""
    state.save(state_path)

    decision_refs: list[str] = []
    if write_wiki:
        conversation_page = project_root / "knowledge" / "llm_wiki" / "conversations" / f"{conversation_key}.md"
        conversation_page.parent.mkdir(parents=True, exist_ok=True)
        conversation_page.write_text(
            "\n".join(
                [
                    f"# Conversation @{brand_handle} -> @{blogger_handle or 'unknown'}",
                    "",
                    "- Status: draft_ready",
                    f"- Channel: {channel}",
                    f"- Draft path: {draft_path.as_posix()}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.append(str(conversation_page))

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Draft prepared for @{brand_handle} and @{blogger_handle or 'unknown'}.",
        confidence="medium",
        outputs={
            "conversation_key": conversation_key,
            "draft_path": str(draft_path),
            "status_path": str(status_path),
            "decision_path": str(task.inputs.get("decision_path", "")),
            "brand_snapshot_path": str(task.inputs.get("brand_snapshot_path", "")),
            "channel": channel,
            "recommended_action": "request_send_approval",
        },
        evidence_refs=[str(draft_path), str(status_path)],
        decision_refs=decision_refs,
    )


def _send_message(project_root: Path, task: AgentTask, *, write_wiki: bool) -> TaskResult:
    if not bool(task.inputs.get("allow_live_send")):
        raise RuntimeError("conversation.send_message requires explicit allow_live_send=true")

    draft_path = Path(str(task.inputs.get("draft_path", "")))
    if not draft_path.exists():
        raise RuntimeError(f"Draft file not found: {draft_path}")
    decision_payload = _load_json(str(task.inputs.get("decision_path", "")))
    snapshot = _load_json(str(task.inputs.get("brand_snapshot_path", "")))

    brand_handle = str(decision_payload.get("brand_handle") or task.entity_refs.get("brand_handle") or "")
    blogger_handle = str(decision_payload.get("blogger_handle") or task.entity_refs.get("blogger_handle") or "")
    channel = str(decision_payload.get("chosen_channel") or task.inputs.get("channel") or "instagram_dm")
    conversation_key = f"{_slug(brand_handle)}__{_slug(blogger_handle or 'unknown')}__{channel}"
    leased_profile_no = str(task.inputs.get("_leased_profile_no") or "")
    if not leased_profile_no:
        raise RuntimeError("Leased profile number is missing for conversation.send_message")
    if channel != "instagram_dm":
        raise RuntimeError(f"conversation.send_message currently supports instagram_dm only, got {channel}")

    target_url = str(snapshot.get("profile_url") or "")
    if not target_url:
        raise RuntimeError("Target profile URL is missing in brand snapshot")

    send_result = asyncio.run(
        _run_instagram_dm_send(
            project_root,
            profile_no=leased_profile_no,
            target_url=target_url,
            draft_text=_extract_draft_body(draft_path),
            conversation_key=conversation_key,
        )
    )

    thread_dir = project_root / "output" / "conversation" / conversation_key
    thread_dir.mkdir(parents=True, exist_ok=True)
    send_status_path = thread_dir / "send_status.json"
    send_status_payload = {
        "conversation_key": conversation_key,
        "status": "sent",
        "channel": channel,
        "brand_handle": brand_handle,
        "blogger_handle": blogger_handle,
        "target_url": target_url,
        **send_result,
    }
    send_status_path.write_text(json.dumps(send_status_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    state_path = project_root / "automation" / "state" / "conversation_state.json"
    state = ConversationState.load(state_path)
    state.current_conversation_key = conversation_key
    thread = state.threads.get(conversation_key, {})
    thread.update(
        {
            "channel": channel,
            "status": "sent",
            "last_message_summary": "Message sent through leased conversation profile.",
            "next_action": "wait_reply",
            "draft_path": str(draft_path),
            "send_status_path": str(send_status_path),
        }
    )
    state.threads[conversation_key] = thread
    if conversation_key not in state.completed_conversation_keys:
        state.completed_conversation_keys.append(conversation_key)
    state.current_conversation_key = ""
    state.save(state_path)

    decision_refs: list[str] = []
    if write_wiki:
        conversation_page = project_root / "knowledge" / "llm_wiki" / "conversations" / f"{conversation_key}.md"
        conversation_page.parent.mkdir(parents=True, exist_ok=True)
        conversation_page.write_text(
            "\n".join(
                [
                    f"# Conversation @{brand_handle} -> @{blogger_handle or 'unknown'}",
                    "",
                    "- Status: sent",
                    f"- Channel: {channel}",
                    f"- Target URL: {target_url}",
                    f"- Send status path: {send_status_path.as_posix()}",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )
        decision_refs.append(str(conversation_page))

    return TaskResult(
        task_id=task.task_id,
        agent=task.assigned_agent,
        status="completed",
        completed_at_iso=utcnow_iso(),
        summary=f"Message sent for @{brand_handle} and @{blogger_handle or 'unknown'}.",
        confidence="medium",
        outputs={
            "conversation_key": conversation_key,
            "send_status_path": str(send_status_path),
            "target_url": target_url,
            "recommended_action": "wait_reply",
        },
        evidence_refs=[str(draft_path), str(send_status_path), str(send_result.get("screenshot_after", ""))],
        decision_refs=decision_refs,
    )


def run_conversation_task(project_root: Path, task: AgentTask, *, write_wiki: bool = True) -> TaskResult:
    if task.task_type == "conversation.prepare_draft":
        return _prepare_draft(project_root, task, write_wiki=write_wiki)
    if task.task_type == "conversation.send_message":
        return _send_message(project_root, task, write_wiki=write_wiki)
    raise RuntimeError(f"Unsupported conversation task type: {task.task_type}")
