from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from ...adspower import AdsPowerClient
from ...artifacts import setup_run_artifacts
from ...browser import capture_screenshot, connect_profile
from ...config import AdsPowerSettings
from .models import BrowserSubagentSpec, BrowserSubagentState
from .state import load_subagent_state, save_subagent_state


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_subagent_specs(job: dict) -> list[BrowserSubagentSpec]:
    specs: list[BrowserSubagentSpec] = []
    for name, raw in (job.get("agents") or {}).items():
        spec = BrowserSubagentSpec(
            name=name,
            role=str(raw.get("role") or name),
            profile_no=str(raw.get("profile_no") or ""),
            start_url=str(raw.get("start_url") or ""),
            purpose=str(raw.get("purpose") or ""),
            enabled=bool(raw.get("enabled", True)),
            keep_browser_open=bool(raw.get("keep_browser_open", True)),
            allowed_channels=[str(item) for item in (raw.get("allowed_channels") or [])],
            writes_messages=bool(raw.get("writes_messages", False)),
            human_approval_required=bool(raw.get("human_approval_required", True)),
            managed_by_module=str(raw.get("managed_by_module") or ""),
            memory_workspace=str(raw.get("memory_workspace") or ""),
            notes=str(raw.get("notes") or ""),
        )
        if spec.enabled:
            specs.append(spec)
    return specs


def build_subagent_paths(job: dict, spec: BrowserSubagentSpec) -> tuple[Path, Path, Path]:
    state_dir = Path(job["state"]["state_dir"])
    output_dir = Path(job["outputs"]["base_dir"]) / spec.name
    return (
        state_dir / f"{spec.name}.json",
        output_dir / "status.md",
        output_dir / "landing.png",
    )


def write_subagent_status(job: dict, spec: BrowserSubagentSpec, state: BrowserSubagentState) -> None:
    state_path, status_md_path, _ = build_subagent_paths(job, spec)
    status_md_path.parent.mkdir(parents=True, exist_ok=True)
    save_subagent_state(state_path, state)

    lines = [
        f"# {spec.role}",
        "",
        f"- Agent name: {spec.name}",
        f"- Profile no: {spec.profile_no}",
        f"- Purpose: {spec.purpose}",
        f"- Status: {state.status}",
        f"- Current URL: {state.current_url or 'none'}",
        f"- Last started: {state.last_started_at_iso or 'none'}",
        f"- Last connected: {state.last_connected_at_iso or 'none'}",
        f"- Last completed: {state.last_completed_at_iso or 'none'}",
        f"- Last artifact dir: {state.last_artifact_dir or 'none'}",
        f"- Last log path: {state.last_log_path or 'none'}",
        f"- Last screenshot: {state.last_screenshot_path or 'none'}",
        f"- Allowed channels: {', '.join(spec.allowed_channels) or 'none'}",
        f"- Writes messages: {'yes' if state.writes_messages else 'no'}",
        f"- Human approval required: {'yes' if state.human_approval_required else 'no'}",
        f"- Managed by module: {state.managed_by_module or 'none'}",
        f"- Memory workspace: {state.memory_workspace or 'none'}",
        f"- Notes: {spec.notes or 'none'}",
        "",
    ]
    status_md_path.write_text("\n".join(lines), encoding="utf-8-sig")


async def start_profile_with_retry(
    client: AdsPowerClient,
    logger: logging.Logger,
    profile_no: str,
    *,
    attempts: int = 4,
    start_delay_sec: float = 0.0,
) -> object:
    if start_delay_sec:
        await asyncio.sleep(start_delay_sec)
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            logger.info("Starting AdsPower profile %s (attempt %s/%s)", profile_no, attempt, attempts)
            return client.start_profile(profile_no=profile_no, last_opened_tabs=False)
        except Exception as exc:
            last_exc = exc
            message = str(exc).lower()
            logger.warning("Profile %s start failed: %s", profile_no, exc)
            if "too many request per second" not in message or attempt == attempts:
                break
            await asyncio.sleep(1.5 * attempt)
    if last_exc is None:
        raise RuntimeError(f"Could not start profile {profile_no}")
    raise last_exc


async def run_subagent_probe(
    project_root: Path,
    job: dict,
    spec: BrowserSubagentSpec,
    *,
    start_delay_sec: float = 0.0,
) -> dict:
    artifacts, logger = setup_run_artifacts(project_root, f"subagent_{spec.name}")
    settings = AdsPowerSettings.from_project_root(project_root)
    client = AdsPowerClient(
        AdsPowerSettings(
            base_url=settings.base_url,
            api_key=settings.api_key,
            profile_no=spec.profile_no,
        )
    )

    state_path, _, screenshot_path = build_subagent_paths(job, spec)
    state = load_subagent_state(state_path)
    state.agent_name = spec.name
    state.role = spec.role
    state.profile_no = spec.profile_no
    state.purpose = spec.purpose
    state.allowed_channels = list(spec.allowed_channels)
    state.writes_messages = spec.writes_messages
    state.human_approval_required = spec.human_approval_required
    state.managed_by_module = spec.managed_by_module
    state.memory_workspace = spec.memory_workspace
    state.status = "starting"
    state.last_started_at_iso = utcnow_iso()
    state.last_artifact_dir = str(artifacts.run_dir)
    state.last_log_path = str(artifacts.log_path)
    write_subagent_status(job, spec, state)

    try:
        async with async_playwright() as playwright:
            started = await start_profile_with_retry(
                client,
                logger,
                spec.profile_no,
                attempts=4,
                start_delay_sec=start_delay_sec,
            )
            logger.info("Started AdsPower profile %s on debug port %s", spec.profile_no, started.debug_port)
            browser, context, connected_page = await connect_profile(playwright, started.ws_puppeteer, logger)
            page = connected_page if connected_page else await context.new_page()
            await page.bring_to_front()
            await page.goto(spec.start_url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                logger.info("Networkidle did not settle for %s; continuing with current DOM", spec.start_url)
            await capture_screenshot(page, screenshot_path, logger)
            await capture_screenshot(page, artifacts.screenshots_dir / "landing.png", logger)

            state.status = "ready"
            state.current_url = page.url
            state.last_connected_at_iso = utcnow_iso()
            state.last_completed_at_iso = utcnow_iso()
            state.last_screenshot_path = str(screenshot_path)
            write_subagent_status(job, spec, state)

            if not spec.keep_browser_open:
                await browser.close()
    except Exception as exc:
        state.status = "failed"
        state.last_completed_at_iso = utcnow_iso()
        state.current_url = state.current_url or spec.start_url
        write_subagent_status(job, spec, state)
        raise exc

    return {
        "agent": spec.name,
        "profile_no": spec.profile_no,
        "url": state.current_url,
        "artifact_dir": str(artifacts.run_dir),
        "log_path": str(artifacts.log_path),
        "screenshot_path": str(screenshot_path),
        "state_path": str(state_path),
    }
