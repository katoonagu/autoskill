from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import capture_screenshot, connect_profile
from automation.config import AdsPowerSettings
from automation.human import Humanizer
from automation.site_recipes.higgsfield import fill_email, open_email_login


async def main() -> None:
    artifacts, logger = setup_run_artifacts(PROJECT_ROOT, "higgsfield_login_fill")
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    client = AdsPowerClient(settings)

    logger.info("Checking AdsPower Local API status")
    logger.info("AdsPower status: %s", client.status())

    started = client.start_profile()
    logger.info("Started profile %s on debug port %s", settings.profile_no, started.debug_port)

    async with async_playwright() as playwright:
        _, _, page = await connect_profile(playwright, started.ws_puppeteer, logger)
        try:
            human = Humanizer(page)
            await open_email_login(page, human, logger)
            await fill_email(
                page,
                human,
                email="test@mail",
                logger=logger,
                screenshot_path=artifacts.screenshots_dir / "higgsfield_email_filled.png",
            )
            logger.info("Success. Browser profile remains open in AdsPower.")
        except Exception:
            await capture_screenshot(page, artifacts.screenshots_dir / "failure.png", logger)
            logger.exception("Runner failed")
            raise


if __name__ == "__main__":
    asyncio.run(main())
