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
from automation.browser import connect_profile
from automation.config import AdsPowerSettings
from automation.human import Humanizer
from automation.site_recipes.genaipro import recover_to_account_selection


async def main() -> None:
    artifacts, logger = setup_run_artifacts(PROJECT_ROOT, "genaipro_restore")
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    client = AdsPowerClient(settings)
    logger.info("AdsPower status: %s", client.status())
    started = client.start_profile(last_opened_tabs=True)
    logger.info("Started profile %s on debug port %s", settings.profile_no, started.debug_port)

    async with async_playwright() as playwright:
        _, _, page = await connect_profile(playwright, started.ws_puppeteer, logger)
        human = Humanizer(page)
        await recover_to_account_selection(
            page,
            human,
            logger,
            screenshot_path=artifacts.screenshots_dir / "restored_account_selection.png",
        )
        logger.info("Restored working page: %s", page.url)


if __name__ == "__main__":
    asyncio.run(main())
