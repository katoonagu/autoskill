from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import yaml
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.adspower import AdsPowerClient
from automation.artifacts import setup_run_artifacts
from automation.browser import connect_profile
from automation.config import AdsPowerSettings
from automation.human import Humanizer
from automation.site_recipes.genaipro import ACCOUNT_SELECTION_URL, run_reference_batch
from automation.state import GenaiproState


def load_job_config() -> dict:
    job_path = PROJECT_ROOT / "automation" / "jobs" / "genaipro_reference_job.yaml"
    return yaml.safe_load(job_path.read_text(encoding="utf-8"))


def choose_best_page(context) -> object:
    def score(page) -> tuple[int, int]:
        url = page.url or ""
        if "genaipro.vn" in url or "veo.genaipro.vn" in url or "labs.google/fx" in url:
            return (2, len(url))
        if url:
            return (1, len(url))
        return (0, 0)

    pages = context.pages
    if not pages:
        return None
    return max(enumerate(pages), key=lambda item: (score(item[1]), item[0]))[1]


async def main() -> None:
    job = load_job_config()
    artifacts, logger = setup_run_artifacts(PROJECT_ROOT, "genaipro_reference_batch")
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    client = AdsPowerClient(settings)

    state_path = Path(job["state"]["state_file"])
    state = GenaiproState.load(state_path)
    prompt_text = Path(job["assets"]["prompt_file"]).read_text(encoding="utf-8").strip()
    reference_input_dir = Path(job["assets"]["reference_input_dir"])
    reference_done_dir = Path(job["assets"]["reference_done_dir"])
    output_dir = Path(job["assets"]["download_output_dir"])
    proxy_fallback_cfg = job.get("proxy_fallback", {})

    logger.info("AdsPower status: %s", client.status())
    started = client.start_profile(last_opened_tabs=job["state"].get("restore_last_context_on_startup", True))
    logger.info("Started profile %s on debug port %s", settings.profile_no, started.debug_port)

    async with async_playwright() as playwright:
        browser, context, page = await connect_profile(playwright, started.ws_puppeteer, logger)
        page = await context.new_page()
        await page.goto(ACCOUNT_SELECTION_URL, wait_until="domcontentloaded", timeout=60000)

        page.set_default_timeout(job["retry_policy"]["selector_timeout_sec"] * 1000)
        human = Humanizer(page)

        used_proxy_ids: set[str] = set()

        async def rotate_proxy_and_reconnect(reference_path: Path, attempt: int, exc: Exception):
            nonlocal browser, context, page, human

            profile = client.get_profile(settings.profile_no)
            current_proxy_id = profile.proxy_id
            if current_proxy_id:
                used_proxy_ids.add(current_proxy_id)

            proxies = client.list_proxies(limit=100)
            candidates = [
                proxy
                for proxy in proxies
                if proxy.proxy_id and proxy.proxy_id != current_proxy_id and proxy.proxy_id not in used_proxy_ids
            ]
            candidates.sort(key=lambda proxy: (proxy.profile_count not in {"0", 0}, proxy.proxy_id))
            if not candidates:
                raise RuntimeError(
                    f"Proxy fallback exhausted for {reference_path.name}; no alternate proxies remain after {current_proxy_id}"
                )

            candidate = candidates[0]
            logger.warning(
                "Rotating proxy for %s after %s. profile=%s current_proxy=%s -> next_proxy=%s (%s:%s)",
                reference_path.name,
                exc,
                settings.profile_no,
                current_proxy_id,
                candidate.proxy_id,
                candidate.host,
                candidate.port,
            )

            try:
                await browser.close()
            except Exception:
                logger.info("Browser close raised during proxy rotation; continuing")

            try:
                stop_result = client.stop_profile(profile_no=settings.profile_no)
                logger.info("AdsPower stop_profile result: %s", stop_result)
            except Exception as stop_exc:
                logger.info("AdsPower stop_profile raised during proxy rotation: %s", stop_exc)

            update_result = client.update_profile_proxy(profile_id=profile.profile_id, proxy_id=candidate.proxy_id)
            logger.info("AdsPower update_profile_proxy result: %s", update_result)

            refreshed_profile = client.get_profile(settings.profile_no)
            used_proxy_ids.add(refreshed_profile.proxy_id)
            logger.info(
                "Profile %s now uses proxy_id=%s host=%s port=%s",
                refreshed_profile.profile_no,
                refreshed_profile.proxy_id,
                refreshed_profile.proxy_host,
                refreshed_profile.proxy_port,
            )

            restarted = client.start_profile(profile_no=settings.profile_no, last_opened_tabs=False)
            logger.info("Restarted profile %s on debug port %s after proxy rotation", settings.profile_no, restarted.debug_port)
            browser, context, page = await connect_profile(playwright, restarted.ws_puppeteer, logger)
            page = await context.new_page()
            await page.goto(ACCOUNT_SELECTION_URL, wait_until="domcontentloaded", timeout=60000)
            page.set_default_timeout(job["retry_policy"]["selector_timeout_sec"] * 1000)
            human = Humanizer(page)
            return page, human

        outputs = await run_reference_batch(
            page,
            human,
            state,
            logger,
            state_path=state_path,
            prompt_text=prompt_text,
            reference_input_dir=reference_input_dir,
            reference_done_dir=reference_done_dir,
            output_dir=output_dir,
            preferred_tiers=job["account_selection"]["preferred_tiers"],
            max_account_attempts=job["retry_policy"]["account_switch_max_attempts"],
            project_name_prefix=job["project_flow"]["project_name_prefix"],
            model_preferences=job["generation_settings"]["model_preference"],
            aspect_ratio=job["generation_settings"]["aspect_ratio"],
            image_count=job["generation_settings"]["image_count"],
            generation_wait_timeout_sec=job["retry_policy"]["generation_wait_timeout_sec"],
            create_fresh_project_per_reference=job["project_flow"].get("create_fresh_project_per_reference", False),
            screenshots_dir=artifacts.screenshots_dir,
            on_proxy_failure=rotate_proxy_and_reconnect if proxy_fallback_cfg.get("enabled", True) else None,
            max_proxy_rotations_per_reference=proxy_fallback_cfg.get("max_proxy_rotations_per_reference", 2),
        )
        logger.info("Batch complete. Generated %s files.", len(outputs))
        for output in outputs:
            logger.info("Output: %s", output)


if __name__ == "__main__":
    asyncio.run(main())
