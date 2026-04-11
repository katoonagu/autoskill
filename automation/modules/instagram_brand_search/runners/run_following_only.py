from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import connect_profile
from automation.config import AdsPowerSettings
from automation.modules.instagram_brand_search.recipe import (
    INSTAGRAM_HOME_URL,
    build_humanizer,
    run_instagram_following_discovery,
)
from automation.modules.instagram_brand_search.runners.run import (
    choose_instagram_page,
    close_extra_tabs,
    load_job_config,
    normalize_job_paths,
)
from automation.modules.instagram_brand_search.state import InstagramBrandSearchState


async def main(force_rescan: bool = False) -> None:
    job = normalize_job_paths(load_job_config())
    artifacts, logger = setup_run_artifacts(PROJECT_ROOT, "instagram_following_only")
    job["_run_dir"] = str(artifacts.run_dir)
    job["_run_label"] = artifacts.run_dir.name
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    settings = AdsPowerSettings(
        base_url=settings.base_url,
        api_key=settings.api_key,
        profile_no=str(job["browser_profile"]["profile_no"]),
    )
    client = AdsPowerClient(settings)
    state_path = Path(job["state"]["state_file"])
    state = InstagramBrandSearchState.load(state_path)

    logger.info("Loaded Instagram following-only job config")
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
        await page.goto(INSTAGRAM_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        human = build_humanizer(page, job)

        try:
            await run_instagram_following_discovery(
                page,
                human,
                logger,
                state,
                job,
                state_path=state_path,
                force_rescan=force_rescan,
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
