from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlparse

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from ..browser import capture_screenshot
from ..human import Humanizer
from ..state import GenaiproState


ACCOUNT_SELECTION_URL = "https://genaipro.vn/veo-account-selection"
FLOW_HOME_URL = "https://veo.genaipro.vn/fx/tools/flow"
PROJECT_URL_RE = re.compile(r"/project/([a-f0-9-]+)", re.IGNORECASE)
BROKEN_EDITOR_HOSTS = {"veo.genaipro.vn", "labs.google"}
BROKEN_PAGE_MARKERS = (
    "404 page not found",
    "there doesn't seem to be anything here.",
    "veo_session_expired",
)


@dataclass
class AccountCandidate:
    row_index: int
    row_text: str
    email: str
    tier: str
    users: int
    action_text: str


class ProxyRotationRequested(RuntimeError):
    pass


def _compact(text: str) -> str:
    return " ".join((text or "").split())


def _button_text(text: str) -> str:
    cleaned = _compact(text)
    for token in (
        "arrow_drop_down",
        "arrow_forward",
        "arrow_back",
        "add_2",
        "crop_16_9",
        "crop_landscape",
        "crop_square",
        "crop_portrait",
        "crop_9_16",
        "image",
        "videocam",
        "upload",
        "folder",
        "download",
        "delete",
        "more_vert",
        "settings_2",
        "dashboard",
        "drive_folder_upload",
        "play_movies",
        "filter_list",
        "search",
    ):
        cleaned = cleaned.replace(token, " ")
    return _compact(cleaned)


def _parse_account_row(row_text: str, row_index: int) -> AccountCandidate | None:
    compact = _compact(row_text)
    match = re.search(
        r"^\d+\s+[A-Z]\s+(\S+@\S+)\s+([\d\s]+)\s+(Ultra|Pro)\s+(\d+)\s+users\s+(Select|Access)$",
        compact,
        re.IGNORECASE,
    )
    if not match:
        return None
    return AccountCandidate(
        row_index=row_index,
        row_text=compact,
        email=match.group(1),
        tier=match.group(3),
        users=int(match.group(4)),
        action_text=match.group(5),
    )


def _project_id_from_url(url: str) -> str:
    match = PROJECT_URL_RE.search(url)
    return match.group(1) if match else ""


def _unique_path(target: Path) -> Path:
    if not target.exists():
        return target
    suffix = target.suffix
    stem = target.stem
    index = 1
    while True:
        candidate = target.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def verified_output_for_reference(reference_path: Path, output_dir: Path) -> Path | None:
    matches = sorted(output_dir.glob(f"{reference_path.stem}_2k.*"))
    return matches[0] if matches else None


def pick_best_runtime_page(current_page: Page, *, prefer_edit: bool = False) -> Page:
    pages = current_page.context.pages
    if not pages:
        return current_page

    def score(page: Page) -> tuple[int, int]:
        url = page.url or ""
        if prefer_edit:
            if "/edit/" in url:
                return (4, len(url))
            if "/project/" in url:
                return (3, len(url))
        else:
            if "/project/" in url and "/edit/" not in url:
                return (4, len(url))
            if "/edit/" in url:
                return (3, len(url))
        if "/project/" in url:
            return (2, len(url))
        if "genaipro.vn" in url or "veo.genaipro.vn" in url:
            return (1, len(url))
        return (0, len(url))

    return max(enumerate(pages), key=lambda item: (score(item[1]), item[0]))[1]


async def _body_text(page: Page) -> str:
    try:
        content = await page.text_content("body")
    except Exception:
        return ""
    return _compact((content or "").lower())


async def is_broken_page(page: Page) -> bool:
    parsed = urlparse(page.url)
    if page.url.startswith(FLOW_HOME_URL) and _project_id_from_url(page.url) == "":
        return False
    if _project_id_from_url(page.url):
        return False
    body_text = await _body_text(page)
    if "veo_session_expired" in page.url:
        return True
    if parsed.netloc in BROKEN_EDITOR_HOSTS and any(marker in body_text for marker in BROKEN_PAGE_MARKERS):
        return True
    if parsed.netloc == "veo.genaipro.vn" and _project_id_from_url(page.url) == "" and page.url.rstrip("/") != FLOW_HOME_URL:
        return "404 page not found" in body_text
    return any(marker in body_text for marker in BROKEN_PAGE_MARKERS)


async def is_account_selection_page(page: Page) -> bool:
    return page.url.startswith(ACCOUNT_SELECTION_URL)


async def is_project_page(page: Page) -> bool:
    return _project_id_from_url(page.url) != ""


async def is_flow_home(page: Page) -> bool:
    return page.url.startswith(FLOW_HOME_URL) and _project_id_from_url(page.url) == ""


async def is_detail_view(page: Page) -> bool:
    done_button = page.locator("button").filter(has_text=re.compile(r"\bDone\b", re.IGNORECASE)).first
    hide_history = page.locator("button").filter(has_text=re.compile(r"Hide history", re.IGNORECASE)).first
    prompt_box = page.locator('[role="textbox"][contenteditable="true"]').first
    if await done_button.count() and await done_button.is_visible():
        return True
    if await hide_history.count() and await hide_history.is_visible():
        return True
    if await prompt_box.count():
        try:
            text = await prompt_box.inner_text()
            if "what do you want to change" in text.lower():
                return True
        except Exception:
            return False
    return False


async def detail_matches_reference(page: Page, reference_path: Path) -> bool:
    if not await is_detail_view(page):
        return False
    body_text = _compact((await page.text_content("body")) or "").lower()
    filename = reference_path.name.lower()
    stem = reference_path.stem.lower()
    short_tail = re.search(r"(\d{6,})", stem)
    tail = short_tail.group(1) if short_tail else ""
    return filename in body_text or stem in body_text or (tail and tail in body_text)


async def leave_mismatched_detail_view(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    go_back = await find_visible_button(
        page,
        lambda text: "go back" in text.lower(),
        choose="first",
    )
    if go_back is not None:
        logger.info("Leaving mismatched detail view via Go Back")
        await human.human_click(go_back)
        await human.pause(1200, 2200)
        return
    done_button = await find_visible_button(
        page,
        lambda text: text.lower() == "done",
        choose="first",
    )
    if done_button is not None:
        logger.info("Leaving mismatched detail view via Done")
        await human.human_click(done_button)
        await human.pause(1200, 2200)
        return


async def close_extension_popup(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    close_button = page.locator('[data-slot="dialog-content"] button').filter(has_text="Close").first
    if await close_button.count() and await close_button.is_visible():
        logger.info("Closing extension popup")
        try:
            await human.human_click(close_button)
            await human.pause(500, 1000)
        except Exception:
            logger.info("Extension popup disappeared during click; continuing")


async def close_cookie_banner(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    ok_button = page.locator("button").filter(has_text=re.compile(r"OK, got it", re.IGNORECASE)).first
    if await ok_button.count() and await ok_button.is_visible():
        logger.info("Closing cookie banner")
        try:
            await human.human_click(ok_button)
            await human.pause(400, 900)
        except Exception:
            logger.info("Cookie banner disappeared during click; continuing")


async def accept_upload_notice_if_present(page: Page, human: Humanizer, logger: logging.Logger) -> bool:
    agree_button = page.locator("button").filter(has_text=re.compile(r"\bI agree\b", re.IGNORECASE)).first
    if await agree_button.count() and await agree_button.is_visible():
        logger.info("Accepting upload notice modal")
        try:
            await human.human_click(agree_button)
            await human.pause(500, 1000)
            return True
        except Exception:
            logger.info("Upload notice disappeared during click; continuing")
    return False


async def recover_to_account_selection(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    screenshot_path: Path | None = None,
) -> None:
    if await is_account_selection_page(page):
        await close_extension_popup(page, human, logger)
        await close_cookie_banner(page, human, logger)
    else:
        logger.info("Recovering browser back to account selection page from %s", page.url)
        await page.goto(ACCOUNT_SELECTION_URL, wait_until="domcontentloaded", timeout=60000)
        await human.pause(1200, 2200)
        await close_extension_popup(page, human, logger)
        await close_cookie_banner(page, human, logger)
    if screenshot_path:
        await capture_screenshot(page, screenshot_path, logger)


async def read_account_candidates(page: Page) -> list[AccountCandidate]:
    rows = page.locator("tr")
    count = await rows.count()
    candidates: list[AccountCandidate] = []
    for index in range(1, count):
        text = await rows.nth(index).inner_text()
        candidate = _parse_account_row(text, index)
        if candidate:
            candidates.append(candidate)
    return candidates


async def wait_for_account_candidates(page: Page, human: Humanizer, timeout_seconds: int = 20) -> list[AccountCandidate]:
    deadline = time.monotonic() + timeout_seconds
    candidates: list[AccountCandidate] = []
    while time.monotonic() < deadline:
        candidates = await read_account_candidates(page)
        if candidates:
            return candidates
        await human.pause(800, 1400)
    return candidates


def sort_account_candidates(
    candidates: list[AccountCandidate],
    state: GenaiproState,
    preferred_tiers: list[str],
) -> list[AccountCandidate]:
    tier_order = {tier.lower(): index for index, tier in enumerate(preferred_tiers)}

    def key(candidate: AccountCandidate) -> tuple[int, int, int, str]:
        saved_priority = 0 if state.account_email and candidate.email == state.account_email else 1
        tier_priority = tier_order.get(candidate.tier.lower(), len(tier_order))
        users_priority = 0 if candidate.users == 0 else 1
        return (saved_priority, users_priority, tier_priority, candidate.email)

    return sorted(candidates, key=key)


async def _visible_buttons(page: Page) -> list[tuple[Locator, str, float]]:
    buttons = page.locator("button")
    count = await buttons.count()
    matches: list[tuple[Locator, str, float]] = []
    for index in range(count):
        button = buttons.nth(index)
        if not await button.is_visible():
            continue
        text = _button_text(await button.inner_text())
        box = await button.bounding_box()
        x = box["x"] if box else float(index)
        matches.append((button, text, x))
    return matches


async def find_visible_button(
    page: Page,
    predicate,
    *,
    choose: str = "first",
) -> Locator | None:
    matches = []
    for button, text, x in await _visible_buttons(page):
        if predicate(text):
            matches.append((button, text, x))
    if not matches:
        return None
    if choose == "rightmost":
        matches.sort(key=lambda item: item[2], reverse=True)
    elif choose == "leftmost":
        matches.sort(key=lambda item: item[2])
    return matches[0][0]


async def click_visible_button(
    page: Page,
    human: Humanizer,
    predicate,
    logger: logging.Logger,
    *,
    choose: str = "first",
    label: str,
) -> bool:
    button = await find_visible_button(page, predicate, choose=choose)
    if button is None:
        return False
    logger.info("Clicking button: %s", label)
    await human.human_click(button)
    return True


async def try_access_account(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    candidate: AccountCandidate,
    logger: logging.Logger,
) -> bool:
    row = page.locator("tr").filter(has_text=candidate.email).first
    if not await row.count():
        return False
    action_button = row.locator("button").first
    action_text = _button_text(await action_button.inner_text())
    if action_text.lower() == "select":
        logger.info("Selecting account row for %s", candidate.email)
        await human.human_click(action_button)
        await human.pause(1000, 1800)
        action_text = _button_text(await action_button.inner_text())

    if action_text.lower() != "access":
        logger.warning("Row for %s did not switch to Access. Current button text: %s", candidate.email, action_text)
        return False

    logger.info("Accessing account %s", candidate.email)
    await human.human_click(action_button)
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except PlaywrightTimeoutError:
        logger.info("Account access did not trigger a full load event; continuing with state checks")
    await human.pause(2500, 4500)
    await close_cookie_banner(page, human, logger)

    if await is_flow_home(page) or await is_project_page(page):
        state.account_email = candidate.email
        state.account_tier = candidate.tier
        state.account_row_text = candidate.row_text
        return True

    if await is_broken_page(page):
        logger.warning("Account %s redirected into broken/session-expired state: %s", candidate.email, page.url)
        return False

    logger.warning("Account %s did not reach flow/project page. Current url: %s", candidate.email, page.url)
    return False


async def ensure_account_access(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    preferred_tiers: list[str],
    max_attempts: int,
) -> None:
    if await is_project_page(page) or await is_flow_home(page):
        return

    tried: set[str] = set()
    for _ in range(max_attempts):
        await recover_to_account_selection(page, human, logger)
        current_candidates = await wait_for_account_candidates(page, human)
        candidates = [
            candidate
            for candidate in sort_account_candidates(current_candidates, state, preferred_tiers)
            if candidate.users == 0 and candidate.email not in tried
        ]
        if not candidates:
            logger.warning("No eligible account candidates are currently available on account selection")
            break
        candidate = candidates[0]
        tried.add(candidate.email)
        if await try_access_account(page, human, state, candidate, logger):
            return

    raise RuntimeError("Unable to access a working Ultra/Pro account on Genaipro")


def update_project_state(state: GenaiproState, project_name_prefix: str, current_url: str) -> None:
    project_id = _project_id_from_url(current_url)
    if project_id:
        state.project_url = f"{FLOW_HOME_URL}/project/{project_id}"
    else:
        state.project_url = current_url
    state.project_id = project_id
    if not state.project_name and project_id:
        state.project_name = f"{project_name_prefix}_{project_id[:8]}"


async def open_saved_project(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    project_name_prefix: str,
) -> bool:
    if not state.project_url:
        return False
    logger.info("Opening saved project context: %s", state.project_url)
    await page.goto(state.project_url, wait_until="domcontentloaded", timeout=60000)
    await human.pause(1800, 3200)
    await close_cookie_banner(page, human, logger)
    if await is_project_page(page):
        update_project_state(state, project_name_prefix, page.url)
        return True
    logger.warning("Saved project context is no longer valid: %s", page.url)
    return False


async def create_new_project(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    project_name_prefix: str,
) -> None:
    if not await is_flow_home(page):
        await page.goto(FLOW_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        await human.pause(1500, 2800)

    new_project = None
    for _ in range(8):
        new_project = await find_visible_button(
            page,
            lambda text: "new project" in text.lower(),
            choose="first",
        )
        if new_project is not None:
            break
        await human.pause(900, 1400)
    if new_project is None:
        raise RuntimeError("New project button not found on Genaipro flow home")

    logger.info("Creating a new project")
    await new_project.click(force=True)
    await human.pause(900, 1500)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        page = pick_best_runtime_page(page)
        if _project_id_from_url(page.url):
            await human.pause(1800, 3200)
            update_project_state(state, project_name_prefix, page.url)
            return
        if await is_flow_home(page):
            edit_button = await find_visible_button(
                page,
                lambda text: "edit project" in text.lower(),
                choose="first",
            )
            if edit_button is not None:
                logger.info("New project stayed on home; opening freshest project via Edit project")
                await edit_button.click(force=True)
                await human.pause(1500, 2400)
        await human.pause(700, 1200)
    raise RuntimeError("New project did not navigate to a project url in time")


async def ensure_project_context(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    preferred_tiers: list[str],
    max_account_attempts: int,
    project_name_prefix: str,
) -> None:
    if await is_broken_page(page):
        await recover_to_account_selection(page, human, logger)

    if await is_project_page(page):
        update_project_state(state, project_name_prefix, page.url)
        return

    if state.project_url and await open_saved_project(page, human, state, logger, project_name_prefix=project_name_prefix):
        return

    await ensure_account_access(
        page,
        human,
        state,
        logger,
        preferred_tiers=preferred_tiers,
        max_attempts=max_account_attempts,
    )

    if state.project_url and await open_saved_project(page, human, state, logger, project_name_prefix=project_name_prefix):
        return

    await create_new_project(page, human, state, logger, project_name_prefix=project_name_prefix)


async def start_fresh_project_for_reference(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    preferred_tiers: list[str],
    max_account_attempts: int,
    project_name_prefix: str,
) -> Page:
    page = pick_best_runtime_page(page)
    if await is_broken_page(page) or await is_account_selection_page(page):
        await ensure_account_access(
            page,
            human,
            state,
            logger,
            preferred_tiers=preferred_tiers,
            max_attempts=max_account_attempts,
        )
        page = pick_best_runtime_page(page)
    if not await is_flow_home(page):
        await page.goto(FLOW_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        await human.pause(1600, 2600)
    await create_new_project(page, human, state, logger, project_name_prefix=project_name_prefix)
    return page


async def open_add_media_menu(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    clicked = await click_visible_button(
        page,
        human,
        lambda text: "add media" in text.lower(),
        logger,
        choose="rightmost",
        label="Add Media",
    )
    if not clicked:
        clicked = await click_visible_button(
            page,
            human,
            lambda text: text.lower() == "create",
            logger,
            choose="rightmost",
            label="Create plus",
        )
    if not clicked:
        plus_button = page.locator('button[aria-haspopup="dialog"]').filter(
            has=page.locator("i", has_text=re.compile(r"^add_2$", re.IGNORECASE))
        ).first
        if await plus_button.count() and await plus_button.is_visible():
            logger.info("Clicking explicit add_2 plus button")
            await human.human_click(plus_button)
            clicked = True
    if not clicked:
        raise RuntimeError("Unable to find Add Media/Create plus button")
    await human.pause(700, 1300)


async def upload_reference_image(
    page: Page,
    human: Humanizer,
    reference_path: Path,
    logger: logging.Logger,
) -> None:
    logger.info("Uploading reference image: %s", reference_path.name)
    upload_button = None
    for attempt in range(3):
        await open_add_media_menu(page, human, logger)
        upload_tile = page.locator("div").filter(has_text=re.compile(r"^Upload image$", re.IGNORECASE)).first
        upload_button = upload_tile
        if await upload_button.count() and await upload_button.is_visible():
            break
        upload_button = await find_visible_button(
            page,
            lambda text: text.lower() in {"upload", "upload image"},
            choose="first",
        )
        if upload_button is not None:
            break
        logger.info("Upload image option did not appear on attempt %s", attempt + 1)
        await human.pause(700, 1200)
    if upload_button is None or not await upload_button.count():
        raise RuntimeError("Upload image option not found")

    chooser = None
    try:
        async with page.expect_file_chooser(timeout=5000) as chooser_info:
            await human.human_click(upload_button)
        chooser = await chooser_info.value
    except PlaywrightTimeoutError:
        logger.info("Upload image did not open file chooser; falling back to file input")

    if chooser is not None:
        await chooser.set_files(str(reference_path))
    else:
        file_inputs = page.locator('input[type="file"]')
        if not await file_inputs.count():
            raise RuntimeError("No file input available after clicking Upload image")
        await file_inputs.last.set_input_files(str(reference_path))

    await accept_upload_notice_if_present(page, human, logger)
    await human.pause(9000, 10500)


async def open_uploaded_image_detail(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    reference_path: Path,
    known_tile_srcs: set[str] | None = None,
) -> bool:
    await accept_upload_notice_if_present(page, human, logger)
    if await is_detail_view(page):
        return True

    view_images = await find_visible_button(
        page,
        lambda text: "view images" in text.lower(),
        choose="first",
    )
    if view_images is not None:
        logger.info("Opening image gallery")
        await human.human_click(view_images)
        await human.pause(1000, 1600)

    filename_targets = [
        reference_path.name,
        reference_path.stem,
        reference_path.stem[: min(len(reference_path.stem), 32)],
    ]
    wait_deadline = time.monotonic() + 15
    saw_filename = False
    while time.monotonic() < wait_deadline:
        for target_text in filename_targets:
            if not target_text:
                continue
            target = page.get_by_text(target_text, exact=False).first
            if not await target.count():
                continue
            saw_filename = True
            try:
                logger.info("Opening uploaded image by filename match: %s", target_text)
                await human.human_click(target)
                await human.pause(1400, 2200)
                if await is_detail_view(page) or "/edit/" in page.url:
                    if await detail_matches_reference(page, reference_path):
                        return True
                    logger.info("Detail opened but does not match target reference yet")
                    await leave_mismatched_detail_view(page, human, logger)
            except Exception:
                logger.info("Filename target did not open detail view: %s", target_text)
        if saw_filename:
            logger.info("Uploaded filename is visible but detail is not open yet; retrying before fallback")
        else:
            logger.info("Waiting for uploaded filename to appear: %s", reference_path.name)
        await human.pause(900, 1300)

    if known_tile_srcs is not None:
        new_tile_deadline = time.monotonic() + 20
        while time.monotonic() < new_tile_deadline:
            tiles = await visible_workspace_tiles(page)
            new_tiles = [(tile, src, x) for tile, src, x in tiles if src not in known_tile_srcs]
            if new_tiles:
                tile, src, _ = new_tiles[-1]
                logger.info("Opening newly appeared workspace tile after upload")
                try:
                    await human.human_click(tile)
                    await human.pause(1500, 2400)
                    if await is_detail_view(page) or "/edit/" in page.url:
                        if await detail_matches_reference(page, reference_path):
                            return True
                        logger.info("New tile opened detail view; accepting it as the uploaded asset")
                        return True
                except Exception:
                    logger.info("New workspace tile click failed; retrying")
            await human.pause(900, 1300)

    uploaded_targets = [
        page.locator("text=Uploaded image").last,
        page.locator('img[alt="Generated image"]').last,
        page.locator("img").last,
    ]
    for index, target in enumerate(uploaded_targets, start=1):
        if not await target.count():
            continue
        try:
            logger.info("Fallback open of uploaded image detail with target #%s", index)
            await human.human_click(target)
            await human.pause(1200, 2200)
            if await is_detail_view(page) or "/edit/" in page.url:
                if await detail_matches_reference(page, reference_path):
                    return True
                logger.info("Fallback target #%s opened a different detail item; leaving it", index)
                await leave_mismatched_detail_view(page, human, logger)
        except Exception:
            logger.info("Target #%s did not open detail view", index)
    return False


async def ensure_generation_settings(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    *,
    model_preferences: list[str],
    aspect_ratio: str,
    image_count: str,
) -> str:
    selected_model = ""
    settings_button = await find_visible_button(
        page,
        lambda text: "nano banana" in text.lower() or "imagen" in text.lower(),
        choose="leftmost",
    )
    if settings_button is None:
        raise RuntimeError("Generation settings button not found")

    current_raw_text = _compact(await settings_button.inner_text())
    current_text = _button_text(current_raw_text)
    aspect_token = f"crop_{aspect_ratio.replace(':', '_')}"
    has_aspect = aspect_ratio in current_text or aspect_token in current_raw_text
    requires_count = not await is_detail_view(page)
    has_count = image_count.lower() in current_text.lower()
    if has_aspect and (has_count or not requires_count):
        for model in model_preferences:
            if model.lower() in current_raw_text.lower() or model.lower() in current_text.lower():
                logger.info("Generation settings already look correct: %s", current_raw_text)
                return model

    logger.info("Opening generation settings popover")
    await human.human_click(settings_button)
    await human.pause(600, 1200)

    await click_visible_button(
        page,
        human,
        lambda text: text.lower() == "image",
        logger,
        choose="first",
        label="Image mode",
    )
    await click_visible_button(
        page,
        human,
        lambda text: text == aspect_ratio,
        logger,
        choose="first",
        label=f"Aspect ratio {aspect_ratio}",
    )
    await click_visible_button(
        page,
        human,
        lambda text: text.lower() == image_count.lower(),
        logger,
        choose="first",
        label=f"Image count {image_count}",
    )

    model_dropdown = await find_visible_button(
        page,
        lambda text: "nano banana" in text.lower() or "imagen" in text.lower(),
        choose="rightmost",
    )
    if model_dropdown is None:
        raise RuntimeError("Model dropdown button not found in settings popover")
    await human.human_click(model_dropdown)
    await human.pause(500, 1000)

    for model in model_preferences:
        option = await find_visible_button(
            page,
            lambda text, model_name=model: text.lower() == model_name.lower(),
            choose="first",
        )
        if option is not None:
            logger.info("Selecting model %s", model)
            await human.human_click(option)
            await human.pause(700, 1300)
            selected_model = model
            break

    if not selected_model:
        raise RuntimeError(f"None of the preferred models were available: {model_preferences}")
    return selected_model


async def prompt_box(page: Page) -> Locator:
    placeholder = page.locator('[data-slate-placeholder="true"]').filter(
        has_text=re.compile(r"What do you want to change\?", re.IGNORECASE)
    ).first
    if await placeholder.count():
        editor = page.locator('[data-slate-editor="true"][contenteditable="true"]').first
        await editor.wait_for(state="visible", timeout=20000)
        return editor
    editor = page.locator('[data-slate-editor="true"][contenteditable="true"]').first
    if await editor.count():
        await editor.wait_for(state="visible", timeout=20000)
        return editor
    box = page.locator('[role="textbox"][contenteditable="true"]').first
    await box.wait_for(state="visible", timeout=20000)
    return box


async def prompt_box_state(page: Page) -> dict[str, object]:
    return await page.evaluate(
        """
        () => {
          const placeholder = [...document.querySelectorAll('[data-slate-placeholder="true"]')]
            .find(el => (el.textContent || '').includes('What do you want to change?'));
          const editor =
            document.querySelector('[data-slate-editor="true"][contenteditable="true"]') ||
            document.querySelector('[role="textbox"][contenteditable="true"]');
          return {
            hasEditor: !!editor,
            textContent: editor ? (editor.textContent || '') : '',
            innerHTML: editor ? (editor.innerHTML || '') : '',
            placeholderVisible: !!placeholder,
          };
        }
        """
    )


async def current_generated_image_src(page: Page) -> str:
    image = page.locator('img[alt="Generated image"]').first
    if not await image.count():
        return ""
    return (await image.get_attribute("src")) or ""


async def has_failed_generation(page: Page) -> bool:
    retry_button = await find_visible_button(
        page,
        lambda text: "retry" in text.lower(),
        choose="first",
    )
    if retry_button is not None:
        return True
    body_text = _compact((await page.text_content("body")) or "").lower()
    return "failed something went wrong" in body_text


async def visible_workspace_tiles(page: Page) -> list[tuple[Locator, str, float]]:
    images = page.locator("img")
    count = await images.count()
    tiles: list[tuple[Locator, str, float]] = []
    for index in range(count):
        image = images.nth(index)
        if not await image.is_visible():
            continue
        box = await image.bounding_box()
        if not box:
            continue
        if box["width"] < 90 or box["height"] < 120:
            continue
        if box["y"] > 420:
            continue
        src = (await image.get_attribute("src")) or f"img-index:{index}"
        tiles.append((image, src, box["x"]))
    tiles.sort(key=lambda item: item[2])
    return tiles


async def submit_prompt(
    page: Page,
    human: Humanizer,
    prompt_text: str,
    logger: logging.Logger,
) -> None:
    box = await prompt_box(page)
    logger.info("Inserting prompt text")
    await box.click(force=True)
    await page.keyboard.press("Control+A")
    await human.pause(20, 80)
    await page.keyboard.press("Backspace")
    await human.pause(40, 120)
    await page.keyboard.type(prompt_text, delay=2)
    await human.pause(120, 240)

    prompt_state = await prompt_box_state(page)
    content = _compact(str(prompt_state.get("textContent") or ""))
    prompt_probe = _compact(prompt_text[:80]).lower()
    if prompt_probe not in content.lower() or bool(prompt_state.get("placeholderVisible")):
        logger.info("Primary prompt typing did not stick, retrying with insert_text fallback")
        await box.click(force=True)
        await page.keyboard.press("Control+A")
        await human.pause(20, 80)
        await page.keyboard.press("Backspace")
        await human.pause(40, 120)
        await page.keyboard.insert_text(prompt_text)
        await human.pause(120, 240)

    prompt_state = await prompt_box_state(page)
    content = _compact(str(prompt_state.get("textContent") or ""))
    if prompt_probe not in content.lower() or bool(prompt_state.get("placeholderVisible")):
        raise RuntimeError("Prompt text was not inserted into the Genaipro composer")

    submit_button = page.locator("button").filter(
        has=page.locator("i", has_text=re.compile(r"^arrow_forward$", re.IGNORECASE))
    ).first
    if not await submit_button.count():
        raise RuntimeError("Arrow-forward submit button not found")
    logger.info("Clicking arrow_forward submit button")
    await submit_button.click(force=True)
    await human.pause(1800, 2600)


async def wait_for_generation_complete(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    *,
    timeout_seconds: int,
    baseline_image_src: str = "",
) -> Page:
    deadline = time.monotonic() + timeout_seconds
    retry_count = 0
    while time.monotonic() < deadline:
        page = pick_best_runtime_page(page, prefer_edit=True)
        if await is_broken_page(page):
            raise RuntimeError(f"Genaipro entered a broken state while waiting for generation: {page.url}")
        if await has_failed_generation(page):
            retry_button = await find_visible_button(
                page,
                lambda text: "retry" in text.lower(),
                choose="first",
            )
            if retry_button is not None and retry_count < 2:
                retry_count += 1
                logger.info("Generation entered failed state; clicking Retry (%s/2)", retry_count)
                await human.human_click(retry_button)
                await human.pause(2500, 3600)
                deadline = time.monotonic() + timeout_seconds
                continue
            raise ProxyRotationRequested("Generation failed and no further retry attempts remain")
        current_src = await current_generated_image_src(page)
        if "/edit/" in page.url and current_src and current_src != baseline_image_src:
            logger.info("Generation appears complete with a new image src")
            return page
        await human.pause(1800, 2600)
    raise RuntimeError(f"Generation did not complete within {timeout_seconds} seconds")


async def download_generated_result(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    output_dir: Path,
    reference_path: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    page = pick_best_runtime_page(page, prefer_edit=True)
    download_button = await find_visible_button(
        page,
        lambda text: text.lower() == "download",
        choose="first",
    )
    if download_button is None:
        raise RuntimeError("Download button not found in detail view")

    for attempt in range(2):
        logger.info("Opening download action (attempt %s)", attempt + 1)
        await human.pause(6500, 7600)
        try:
            async with page.expect_download(timeout=5000) as download_info:
                await human.human_click(download_button)
            download = await download_info.value
            suggested = Path(download.suggested_filename)
            extension = suggested.suffix or reference_path.suffix or ".png"
            target = _unique_path(output_dir / f"{reference_path.stem}_2k{extension}")
            await download.save_as(str(target))
            if target.exists() and target.stat().st_size >= 100_000:
                logger.info("Saved generated result -> %s", target)
                return target
        except PlaywrightTimeoutError:
            logger.info("Direct download event did not fire; looking for 2K option")

        option = await find_visible_button(
            page,
            lambda text: "2k" in text.lower(),
            choose="first",
        )
        if option is not None:
            logger.info("Downloading generated result in 2K")
            try:
                async with page.expect_download(timeout=60000) as download_info:
                    await human.human_click(option)
                download = await download_info.value
                suggested = Path(download.suggested_filename)
                extension = suggested.suffix or reference_path.suffix or ".png"
                target = _unique_path(output_dir / f"{reference_path.stem}_2k{extension}")
                await download.save_as(str(target))
                if target.exists() and target.stat().st_size >= 100_000:
                    logger.info("Saved generated result -> %s", target)
                    return target
            except PlaywrightTimeoutError:
                logger.info("2K download did not complete on attempt %s", attempt + 1)

        await human.pause(1500, 2200)

    logger.info("Falling back to downloading the currently visible generated image source")
    image_src = await current_generated_image_src(page)
    if not image_src:
        raise RuntimeError("No generated image element found for download fallback")
    response = await page.context.request.get(urljoin(page.url, image_src))
    if not response.ok:
        raise RuntimeError(f"Fallback image download failed with status {response.status}")
    content_type = (response.headers.get("content-type") or "").lower()
    extension = ".png"
    if "jpeg" in content_type or "jpg" in content_type:
        extension = ".jpg"
    elif "webp" in content_type:
        extension = ".webp"
    target = _unique_path(output_dir / f"{reference_path.stem}_2k{extension}")
    target.write_bytes(await response.body())
    if not target.exists() or target.stat().st_size < 100_000:
        raise RuntimeError(f"Fallback image download failed validation: {target}")
    logger.info("Saved generated result via image fallback -> %s", target)
    return target


def move_reference_to_done(reference_path: Path, reference_done_dir: Path, logger: logging.Logger) -> Path:
    reference_done_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_path(reference_done_dir / reference_path.name)
    logger.info("Moving processed reference -> %s", target)
    shutil.move(str(reference_path), str(target))
    return target


async def return_to_project_workspace(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
) -> None:
    done_button = await find_visible_button(
        page,
        lambda text: text.lower() == "done",
        choose="first",
    )
    if done_button is not None:
        logger.info("Returning to project workspace via Done button")
        await human.human_click(done_button)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            page = pick_best_runtime_page(page)
            add_media = await find_visible_button(
                page,
                lambda text: "add media" in text.lower() or text.lower() == "create",
                choose="first",
            )
            if add_media is not None or await is_project_page(page):
                await human.pause(800, 1400)
                return
            await human.pause(700, 1200)

    if state.project_url:
        logger.info("Returning to project workspace via saved project url")
        await page.goto(state.project_url, wait_until="domcontentloaded", timeout=60000)
        for _ in range(8):
            add_media = await find_visible_button(
                page,
                lambda text: "add media" in text.lower() or text.lower() == "create",
                choose="first",
            )
            if add_media is not None:
                await human.pause(600, 1200)
                return
            await human.pause(700, 1200)
        return

    go_back = await find_visible_button(
        page,
        lambda text: "go back" in text.lower(),
        choose="first",
    )
    if go_back is None:
        raise RuntimeError("Unable to return to project workspace: no project url and no Go Back button")
    await human.human_click(go_back)
    await human.pause(1400, 2400)


async def process_reference(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    reference_path: Path,
    prompt_text: str,
    output_dir: Path,
    reference_done_dir: Path,
    model_preferences: list[str],
    aspect_ratio: str,
    image_count: str,
    generation_wait_timeout_sec: int,
) -> Path:
    page = pick_best_runtime_page(page)
    expected_project_url = state.project_url or ""
    if expected_project_url and page.url.rstrip("/") != expected_project_url.rstrip("/") and "/edit/" not in page.url:
        logger.info("Switching explicitly to saved project workspace: %s", expected_project_url)
        await page.goto(expected_project_url, wait_until="domcontentloaded", timeout=60000)
        await human.pause(1400, 2200)
        await close_cookie_banner(page, human, logger)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        page = pick_best_runtime_page(page)
        file_inputs = page.locator('input[type="file"]')
        add_media = await find_visible_button(
            page,
            lambda text: "add media" in text.lower(),
            choose="first",
        )
        if await file_inputs.count() or add_media is not None:
            break
        if expected_project_url:
            await page.goto(expected_project_url, wait_until="domcontentloaded", timeout=60000)
        await human.pause(900, 1400)
    page = pick_best_runtime_page(page, prefer_edit=True)
    if "/edit/" in page.url:
        await return_to_project_workspace(page, human, state, logger)
        page = pick_best_runtime_page(page)
    known_tile_srcs = {src for _, src, _ in await visible_workspace_tiles(page)}
    await upload_reference_image(page, human, reference_path, logger)
    opened_detail = False
    for attempt in range(3):
        opened_detail = await open_uploaded_image_detail(
            page,
            human,
            logger,
            reference_path,
            known_tile_srcs=known_tile_srcs,
        )
        if opened_detail:
            break
        logger.info("Uploaded image detail not ready for %s on attempt %s", reference_path.name, attempt + 1)
        await human.pause(4500, 6500)
    logger.info("Opened detail view after upload: %s", opened_detail)
    if not opened_detail:
        raise RuntimeError(f"Uploaded image detail did not open for {reference_path.name}")
    selected_model = await ensure_generation_settings(
        page,
        human,
        logger,
        model_preferences=model_preferences,
        aspect_ratio=aspect_ratio,
        image_count=image_count,
    )
    logger.info("Using model: %s", selected_model)
    baseline_image_src = await current_generated_image_src(page)
    await submit_prompt(page, human, prompt_text, logger)
    page = await wait_for_generation_complete(
        page,
        human,
        logger,
        timeout_seconds=generation_wait_timeout_sec,
        baseline_image_src=baseline_image_src,
    )
    saved_output = await download_generated_result(page, human, logger, output_dir, reference_path)
    move_reference_to_done(reference_path, reference_done_dir, logger)
    await return_to_project_workspace(page, human, state, logger)
    return saved_output


async def run_reference_batch(
    page: Page,
    human: Humanizer,
    state: GenaiproState,
    logger: logging.Logger,
    *,
    state_path: Path,
    prompt_text: str,
    reference_input_dir: Path,
    reference_done_dir: Path,
    output_dir: Path,
    preferred_tiers: list[str],
    max_account_attempts: int,
    project_name_prefix: str,
    model_preferences: list[str],
    aspect_ratio: str,
    image_count: str,
    generation_wait_timeout_sec: int,
    create_fresh_project_per_reference: bool = False,
    screenshots_dir: Path | None = None,
    on_proxy_failure: Callable[[Path, int, Exception], Awaitable[tuple[Page, Humanizer]]] | None = None,
    max_proxy_rotations_per_reference: int = 0,
) -> list[Path]:
    await ensure_project_context(
        page,
        human,
        state,
        logger,
        preferred_tiers=preferred_tiers,
        max_account_attempts=max_account_attempts,
        project_name_prefix=project_name_prefix,
    )
    state.save(state_path)

    references = sorted(path for path in reference_input_dir.iterdir() if path.is_file())
    for reference_path in references:
        verified_output = verified_output_for_reference(reference_path, output_dir)
        already_done = (reference_done_dir / reference_path.name).exists()
        if verified_output or already_done:
            if reference_path.exists() and not already_done:
                move_reference_to_done(reference_path, reference_done_dir, logger)
            state.mark_completed(reference_path.name)

    references = sorted(path for path in reference_input_dir.iterdir() if path.is_file())
    pending = [
        path
        for path in references
        if verified_output_for_reference(path, output_dir) is None
    ]
    if state.current_reference:
        current_index = next((index for index, path in enumerate(pending) if path.name == state.current_reference), None)
        if current_index is not None:
            pending = pending[current_index:] + pending[:current_index]
    if not pending:
        logger.info("No pending references found in %s", reference_input_dir)
        state.save(state_path)
        return []

    outputs: list[Path] = []
    for reference_path in pending:
        logger.info("Processing reference %s", reference_path.name)
        proxy_rotation_attempts = 0
        while True:
            state.current_reference = reference_path.name
            state.save(state_path)
            try:
                if page.is_closed():
                    logger.info("Current page is closed; opening a fresh page from account selection")
                    page = await page.context.new_page()
                    await page.goto(ACCOUNT_SELECTION_URL, wait_until="domcontentloaded", timeout=60000)
                    human = Humanizer(page)
                if await is_broken_page(page):
                    await ensure_project_context(
                        page,
                        human,
                        state,
                        logger,
                        preferred_tiers=preferred_tiers,
                        max_account_attempts=max_account_attempts,
                        project_name_prefix=project_name_prefix,
                    )
                if create_fresh_project_per_reference:
                    page = await start_fresh_project_for_reference(
                        page,
                        human,
                        state,
                        logger,
                        preferred_tiers=preferred_tiers,
                        max_account_attempts=max_account_attempts,
                        project_name_prefix=project_name_prefix,
                    )
                    state.save(state_path)
                else:
                    await ensure_project_context(
                        page,
                        human,
                        state,
                        logger,
                        preferred_tiers=preferred_tiers,
                        max_account_attempts=max_account_attempts,
                        project_name_prefix=project_name_prefix,
                    )
                    page = pick_best_runtime_page(page)
                output = await process_reference(
                    page,
                    human,
                    state,
                    logger,
                    reference_path=reference_path,
                    prompt_text=prompt_text,
                    output_dir=output_dir,
                    reference_done_dir=reference_done_dir,
                    model_preferences=model_preferences,
                    aspect_ratio=aspect_ratio,
                    image_count=image_count,
                    generation_wait_timeout_sec=generation_wait_timeout_sec,
                )
                outputs.append(output)
                state.mark_completed(reference_path.name)
                state.save(state_path)
                if screenshots_dir is not None:
                    safe_name = reference_path.stem.replace(" ", "_")
                    await capture_screenshot(page, screenshots_dir / f"{safe_name}_completed.png", logger)
                break
            except ProxyRotationRequested as exc:
                if on_proxy_failure is not None and proxy_rotation_attempts < max_proxy_rotations_per_reference:
                    proxy_rotation_attempts += 1
                    logger.warning(
                        "Proxy fallback requested for %s (%s/%s)",
                        reference_path.name,
                        proxy_rotation_attempts,
                        max_proxy_rotations_per_reference,
                    )
                    page, human = await on_proxy_failure(reference_path, proxy_rotation_attempts, exc)
                    continue
                if screenshots_dir is not None:
                    try:
                        safe_name = reference_path.stem.replace(" ", "_")
                        await capture_screenshot(page, screenshots_dir / f"{safe_name}_failure.png", logger)
                    except Exception:
                        logger.exception("Failed to capture failure screenshot")
                logger.exception("Failed processing reference %s; continuing with the next file", reference_path.name)
                break
            except Exception:
                if screenshots_dir is not None:
                    try:
                        safe_name = reference_path.stem.replace(" ", "_")
                        await capture_screenshot(page, screenshots_dir / f"{safe_name}_failure.png", logger)
                    except Exception:
                        logger.exception("Failed to capture failure screenshot")
                logger.exception("Failed processing reference %s; continuing with the next file", reference_path.name)
                break
    return outputs
