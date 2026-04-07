from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from playwright.async_api import async_playwright

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import connect_profile
from automation.config import AdsPowerSettings
from automation.modules.instagram_brand_search.recipe import INSTAGRAM_HOME_URL, build_humanizer, run_instagram_brand_search
from automation.modules.instagram_brand_search.state import InstagramBrandSearchState


def load_job_config() -> dict:
    job_path = PROJECT_ROOT / "automation" / "modules" / "instagram_brand_search" / "job.yaml"
    return yaml.safe_load(job_path.read_text(encoding="utf-8"))


async def choose_instagram_page(context) -> object:
    best = None
    best_score = (-1, -1)
    for index, page in enumerate(context.pages):
        try:
            url = page.url or ""
            score = 0
            if "instagram.com" in url:
                score += 4
            if "/p/" in url or "/reel/" in url:
                score += 2
            body_len = await page.evaluate("() => (document.body && document.body.innerText || '').length")
            if body_len > 200:
                score += 3
            elif body_len > 20:
                score += 1
            candidate_score = (score, index)
            if candidate_score > best_score:
                best = page
                best_score = candidate_score
        except Exception:
            continue
    return best


async def close_extra_tabs(context, main_page, logger) -> None:
    for page in list(context.pages):
        if page == main_page:
            continue
        try:
            logger.info("Closing extra tab: %s", page.url)
            await page.close()
        except Exception as exc:
            logger.info("Failed to close extra tab %s: %s", page.url, exc)


async def main() -> None:
    job = load_job_config()
    artifacts, logger = setup_run_artifacts(PROJECT_ROOT, "instagram_brand_search")
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    settings = AdsPowerSettings(
        base_url=settings.base_url,
        api_key=settings.api_key,
        profile_no=str(job["browser_profile"]["profile_no"]),
    )
    client = AdsPowerClient(settings)
    state_path = Path(job["state"]["state_file"])
    state = InstagramBrandSearchState.load(state_path)

    logger.info("Loaded Instagram job config")
    logger.info("AdsPower status: %s", client.status())

    async with async_playwright() as playwright:
        started = client.start_profile(
            profile_no=settings.profile_no,
            last_opened_tabs=job["state"].get("restore_last_context_on_startup", True),
        )
        logger.info("Started AdsPower profile %s on debug port %s", settings.profile_no, started.debug_port)
        browser, context, connected_page = await connect_profile(playwright, started.ws_puppeteer, logger)
        page = await choose_instagram_page(context) or connected_page
        if "instagram.com" not in (page.url or ""):
            page = await context.new_page()
        await close_extra_tabs(context, page, logger)
        await page.bring_to_front()
        page.set_default_timeout(job["retry_policy"]["selector_timeout_sec"] * 1000)
        body_len = await page.evaluate("() => (document.body && document.body.innerText || '').length")
        if "instagram.com" not in (page.url or "") or body_len < 100:
            await page.goto(INSTAGRAM_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        human = build_humanizer(page, job)

        try:
            await run_instagram_brand_search(
                page,
                human,
                logger,
                state,
                job,
                state_path=state_path,
            )
        finally:
            state.save(state_path)
            logger.info("Artifacts written to %s", artifacts.run_dir)
            try:
                await browser.close()
            except Exception:
                logger.info("Browser close failed during shutdown; ignoring")


if __name__ == "__main__":
    asyncio.run(main())
