from __future__ import annotations

from pathlib import Path
from typing import Tuple
import logging

from playwright.async_api import Browser, BrowserContext, Page, Playwright


async def connect_profile(
    playwright: Playwright,
    ws_endpoint: str,
    logger: logging.Logger,
) -> Tuple[Browser, BrowserContext, Page]:
    logger.info("Connecting to browser profile over CDP")
    browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()
    return browser, context, page


async def capture_screenshot(page: Page, target: Path, logger: logging.Logger) -> None:
    logger.info("Saving screenshot -> %s", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(target), full_page=False)

