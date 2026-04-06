from __future__ import annotations

from pathlib import Path
import logging

from playwright.async_api import Locator, Page

from ..browser import capture_screenshot
from ..human import Humanizer


def _cookie_overlay(page: Page) -> Locator:
    return page.locator("#cookiescript_injected_wrapper")


def _login_link(page: Page) -> Locator:
    return page.get_by_text("Login", exact=True).first


def _email_input(page: Page) -> Locator:
    return page.locator(
        'input[type="email"], input[name*="email" i], input[placeholder*="email" i], input[placeholder*="mail" i]'
    ).first


async def dismiss_cookie_overlay(page: Page, logger: logging.Logger) -> None:
    overlay = _cookie_overlay(page)
    if await overlay.count():
        logger.info("Removing cookie overlay before interaction")
        await page.evaluate(
            """
            (() => {
              const el = document.querySelector('#cookiescript_injected_wrapper');
              if (el) el.remove();
            })()
            """
        )


async def open_email_login(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    logger.info("Opening Higgsfield home page")
    await page.goto("https://higgsfield.ai/", wait_until="domcontentloaded", timeout=60000)
    await human.pause(1200, 2200)
    await dismiss_cookie_overlay(page, logger)
    logger.info("Clicking Login entrypoint")
    await human.human_click(_login_link(page))
    await human.pause(1200, 2000)
    if "/auth/email/sign-in" not in page.url:
        logger.info("Ensuring deterministic navigation to email login screen")
        await page.goto("https://higgsfield.ai/auth/email/sign-in?rp=%2F", wait_until="domcontentloaded", timeout=60000)
        await human.pause(1200, 2200)


async def fill_email(page: Page, human: Humanizer, email: str, logger: logging.Logger, screenshot_path: Path) -> None:
    input_locator = _email_input(page)
    logger.info("Filling Higgsfield email field")
    await input_locator.wait_for(state="visible", timeout=30000)
    await human.human_type(input_locator, email)
    await capture_screenshot(page, screenshot_path, logger)
