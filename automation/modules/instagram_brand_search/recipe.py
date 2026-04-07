from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
import logging
import os
import re
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Locator, Page, TimeoutError as PlaywrightTimeoutError

from ...browser import capture_screenshot
from ...human import HumanSettings, Humanizer
from .models import BloggerRunStats, BloggerTarget, BrandAssessment, MentionCandidate, PostSnapshot
from .state import InstagramBrandSearchState


INSTAGRAM_HOME_URL = "https://www.instagram.com/"
POST_LINK_RE = re.compile(r"instagram\.com/(?:[A-Za-z0-9._]+/)?(?:p|reel)/([A-Za-z0-9_-]+)/?", re.IGNORECASE)
PROFILE_LINK_RE = re.compile(r"instagram\.com/([A-Za-z0-9._]+)/?$", re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9._]{1,30})")
AD_KEYWORDS = (
    "реклама",
    "промокод",
    "скидк",
    "заказ",
    "shop",
    "store",
    "collection",
    "brand",
    "collab",
    "partnership",
    "sponsored",
    "partner",
    "thanks to",
    "wearing",
    "look from",
    "dress by",
    "shop now",
)
BRAND_KEYWORDS = (
    "official",
    "shop",
    "store",
    "atelier",
    "collection",
    "denim",
    "beauty",
    "cosmetic",
    "cosmetics",
    "boutique",
    "supplement",
    "nutrition",
    "fit",
    "sport",
    "flower",
    "flowers",
    "studio",
    "brand",
    "wear",
    "бренд",
    "магазин",
    "салон",
    "клиника",
    "ресторан",
    "кафе",
    "доставка",
    "массаж",
    "косметолог",
    "студия",
)
PERSON_KEYWORDS = (
    "mom",
    "blogger",
    "personal",
    "photographer",
    "traveler",
    "life",
    "journal",
    "model",
    "influencer",
    "creator",
    "stylist",
    "trainer",
    "coach",
    "photography",
    "фотограф",
    "блогер",
    "модель",
    "тренер",
    "коуч",
    "стилист",
    "психолог",
    "врач",
    "доктор",
    "ортопед",
    "хирург",
)
SERVICE_KEYWORDS = (
    "photographer",
    "photography",
    "beauty",
    "makeup",
    "stylist",
    "hair",
    "trainer",
    "coach",
    "doctor",
    "clinic",
    "massage",
    "cosmetolog",
    "косметолог",
    "визажист",
    "макияж",
    "фотограф",
    "стилист",
    "парикмахер",
    "тренер",
    "коуч",
    "врач",
    "доктор",
    "клиника",
    "массаж",
    "съёмки",
    "съемки",
    "брендов",
)
PROJECT_KEYWORDS = (
    "charity",
    "shelter",
    "media",
    "project",
    "animal",
    "rescue",
    "благотвор",
    "приют",
    "проект",
    "медиа",
    "спасение",
)


def _compact(text: str) -> str:
    return " ".join((text or "").split())


def _lower_set(items: list[str]) -> set[str]:
    return {item.lower() for item in items if item}


def normalize_text(value: str) -> str:
    text = unescape((value or "").replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    return text.strip()


def md_link(label: str, target: str) -> str:
    safe_label = label.replace("[", "\\[").replace("]", "\\]")
    safe_target = (target or "").replace(" ", "%20")
    return f"[{safe_label}]({safe_target})"


def relative_markdown_target(report_path: Path, target: str) -> str:
    if not target:
        return ""
    target_path = Path(target)
    if not target_path.is_absolute():
        return target_path.as_posix()
    try:
        rel = os.path.relpath(target_path, report_path.parent)
        return Path(rel).as_posix()
    except ValueError:
        return target_path.as_posix()


def canonical_handle(handle: str) -> str:
    return re.sub(r"[._]+", "", (handle or "").strip().lower())


def normalize_instagram_url(raw_url: str) -> str:
    text = raw_url.strip()
    if not text:
        return ""
    if not text.startswith("http"):
        text = f"https://www.instagram.com/{text.lstrip('@').strip('/')}/"
    parsed = urlparse(text)
    cleaned = f"https://www.instagram.com{parsed.path}"
    if not cleaned.endswith("/"):
        cleaned += "/"
    return cleaned


def extract_shortcode(post_url: str) -> str:
    match = POST_LINK_RE.search(post_url or "")
    return match.group(1) if match else ""


def extract_handle_from_url(profile_url: str) -> str:
    match = PROFILE_LINK_RE.search((profile_url or "").rstrip("/"))
    return match.group(1) if match else ""


def candidate_key(post_url: str, handle: str) -> str:
    return f"{post_url}::{handle.lower()}"


def should_skip_line(raw_line: str) -> bool:
    stripped = raw_line.strip()
    return not stripped or stripped.startswith("#")


def load_blogger_targets(path: Path) -> list[BloggerTarget]:
    targets: list[BloggerTarget] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if should_skip_line(raw_line):
            continue
        url = normalize_instagram_url(raw_line)
        if not url:
            continue
        targets.append(BloggerTarget(profile_url=url, handle=extract_handle_from_url(url)))
    return targets


def build_humanizer(page: Page, job: dict) -> Humanizer:
    policy = job.get("humanization_policy", {})
    settings = HumanSettings(
        pause_range_ms=(policy.get("min_pause_ms", 85), policy.get("max_pause_ms", 420)),
        think_range_ms=(180, 420),
        click_delay_ms=(30, 75),
        type_delay_ms=(18, 38),
        move_steps=(8, 14),
        click_jitter_ratio=0.08,
        stability_checks=2,
        stability_interval_ms=90,
    )
    return Humanizer(page, settings=settings)


async def dismiss_instagram_popups(page: Page, human: Humanizer, logger: logging.Logger) -> None:
    patterns = [
        r"^Not now$",
        r"^Close$",
        r"^Cancel$",
        r"^Dismiss$",
    ]
    for pattern in patterns:
        button = page.locator("button").filter(has_text=re.compile(pattern, re.IGNORECASE)).first
        if await button.count():
            try:
                if await button.is_visible():
                    logger.info("Closing Instagram popup with button pattern %s", pattern)
                    await human.human_click(button)
                    await human.pause(350, 800)
            except Exception:
                logger.info("Popup disappeared while closing")


async def profile_page_has_posts(page: Page) -> bool:
    try:
        count = await page.locator('a[href*="/p/"], a[href*="/reel/"]').count()
        return count > 0
    except Exception:
        return False


async def ensure_profile_page(page: Page, human: Humanizer, logger: logging.Logger, profile_url: str) -> None:
    current = normalize_instagram_url(page.url) if page.url else ""
    if current == profile_url and await profile_page_has_posts(page):
        await dismiss_instagram_popups(page, human, logger)
        return

    await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
    await human.pause(1500, 2400)
    await dismiss_instagram_popups(page, human, logger)
    for _ in range(5):
        if await profile_page_has_posts(page):
            return
        await human.pause(800, 1200)
    logger.info("Profile grid not ready after initial navigation; reloading %s", profile_url)
    await page.reload(wait_until="domcontentloaded", timeout=60000)
    await human.pause(1500, 2200)
    await dismiss_instagram_popups(page, human, logger)


async def return_to_profile_from_post(page: Page, human: Humanizer, logger: logging.Logger, profile_url: str) -> None:
    current = normalize_instagram_url(page.url) if page.url else ""
    if current == profile_url and await profile_page_has_posts(page):
        return

    for _ in range(2):
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=30000)
            await human.pause(700, 1200)
            if normalize_instagram_url(page.url) == profile_url and await profile_page_has_posts(page):
                await dismiss_instagram_popups(page, human, logger)
                return
        except Exception:
            break

    await ensure_profile_page(page, human, logger, profile_url)


async def visible_post_links(page: Page) -> list[tuple[str, bool]]:
    anchors = page.locator('a[href*="/p/"], a[href*="/reel/"]')
    count = await anchors.count()
    results: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for index in range(min(count, 24)):
        anchor = anchors.nth(index)
        try:
            if not await anchor.is_visible():
                continue
            href = await anchor.get_attribute("href")
            if not href:
                continue
            if href.startswith("/"):
                href = f"https://www.instagram.com{href}"
            href = href.split("?", 1)[0].rstrip("/") + "/"
            if href in seen:
                continue
            seen.add(href)
            html = (await anchor.inner_html()).lower()
            pinned = "pinned" in html
            results.append((href, pinned))
        except Exception:
            continue
    return results


async def open_profile_post_from_grid(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    *,
    target_post_url: str = "",
) -> Page:
    chosen_url = target_post_url
    shortcode = extract_shortcode(chosen_url) if chosen_url else ""
    max_scroll_attempts = 18 if target_post_url else 1
    target_anchor = None
    for _ in range(max_scroll_attempts):
        links = await visible_post_links(page)
        if not links:
            raise RuntimeError("No visible Instagram posts found on profile grid")

        if not chosen_url:
            pinned = [url for url, is_pinned in links if is_pinned]
            chosen_url = pinned[0] if pinned else links[0][0]
            shortcode = extract_shortcode(chosen_url)

        anchor = page.locator(f'a[href*="/{shortcode}/"]').first
        if await anchor.count():
            target_anchor = anchor
            break
        if not target_post_url:
            break
        await human.human_wheel_scroll(1400)
        await human.pause(650, 1100)

    if target_anchor is None:
        raise RuntimeError(f"Target post anchor not found for shortcode {shortcode}")

    logger.info("Opening post %s from profile grid", chosen_url)
    existing_pages = list(page.context.pages)
    await human.human_click(target_anchor)
    deadline = datetime.now(timezone.utc) + timedelta(seconds=15)
    while datetime.now(timezone.utc) < deadline:
        if extract_shortcode(page.url) == shortcode:
            await human.pause(650, 1200)
            return page
        for candidate in page.context.pages:
            if candidate in existing_pages:
                continue
            if extract_shortcode(candidate.url) == shortcode:
                await candidate.bring_to_front()
                await human.pause(650, 1200)
                return candidate
        await human.pause(300, 550)
    logger.info("Grid click did not produce an active post page; falling back to direct navigation %s", chosen_url)
    await page.goto(chosen_url, wait_until="domcontentloaded", timeout=60000)
    await human.pause(900, 1500)
    if extract_shortcode(page.url) != shortcode:
        raise RuntimeError(f"Profile post did not open for {chosen_url}")
    return page


async def has_next_post_navigation(page: Page) -> bool:
    buttons = page.locator("button")
    count = await buttons.count()
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    for index in range(count):
        button = buttons.nth(index)
        try:
            if not await button.is_visible():
                continue
            aria = (_compact(await button.get_attribute("aria-label") or "")).lower()
            text = _compact((await button.inner_text()) or "").lower()
            html = ((await button.inner_html()) or "").lower()
            if aria != "next" and "next" not in text and 'aria-label="next"' not in html and ">next<" not in html:
                continue
            box = await button.bounding_box()
            if not box:
                continue
            if box["x"] >= viewport["width"] * 0.55:
                return True
        except Exception:
            continue
    return False


async def reopen_post_modal(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    blogger_url: str,
    post_url: str,
) -> Page:
    target_shortcode = extract_shortcode(post_url)
    if target_shortcode and extract_shortcode(page.url) == target_shortcode:
        await human.pause(450, 800)
        return page

    logger.info("Reopening saved post from profile grid: %s", post_url)
    await ensure_profile_page(page, human, logger, blogger_url)
    for _ in range(3):
        try:
            return await open_profile_post_from_grid(
                page,
                human,
                logger,
                target_post_url=post_url,
            )
        except Exception:
            await human.human_wheel_scroll(900)
            await human.pause(500, 900)
    raise RuntimeError(f"Could not reopen saved post modal for {post_url}")


async def open_next_post_from_profile_grid(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    blogger_url: str,
    current_post_url: str,
) -> Page | None:
    current_shortcode = extract_shortcode(current_post_url)
    if not current_shortcode:
        return None
    await return_to_profile_from_post(page, human, logger, blogger_url)
    links = await visible_post_links(page)
    ordered = [url for url, _ in links]
    try:
        current_index = next(index for index, url in enumerate(ordered) if extract_shortcode(url) == current_shortcode)
    except StopIteration:
        return None
    if current_index + 1 >= len(ordered):
        return None
    next_url = ordered[current_index + 1]
    logger.info("Falling back to grid-based next post: %s", next_url)
    return await open_profile_post_from_grid(page, human, logger, target_post_url=next_url)


async def read_post_snapshot(page: Page, blogger_handle: str) -> PostSnapshot:
    data = await page.evaluate(
        """() => {
            const visible = (el) => !!(el && el.offsetParent);
            const toHandle = (href) => {
              if (!href) return "";
              const m = href.match(/^\\/([^/?#]+)\\/?$/);
              return m ? m[1] : "";
            };
            const authors = [];
            const headerLinks = Array.from(document.querySelectorAll('header a[href^="/"]'));
            for (const link of headerLinks) {
              if (!visible(link)) continue;
              const handle = toHandle(link.getAttribute('href'));
              if (!handle) continue;
              if (!authors.includes(handle)) authors.push(handle);
              if (authors.length >= 2) break;
            }

            let caption = "";
            const h1 = Array.from(document.querySelectorAll('h1[dir="auto"], h1')).find(visible);
            if (h1) {
              caption = (h1.innerText || "").trim();
            }
            if (!caption) {
              const article = document.querySelector('article') || document.querySelector('main');
              if (article) {
                const authorSet = new Set(authors.map(x => x.toLowerCase()));
                const items = Array.from(article.querySelectorAll('ul li')).filter(visible);
                let best = "";
                for (const item of items) {
                  const firstLink = Array.from(item.querySelectorAll('a[href^="/"]')).find(visible);
                  const handle = firstLink ? toHandle(firstLink.getAttribute('href')) : "";
                  if (!handle || !authorSet.has(handle.toLowerCase())) continue;
                  let text = (item.innerText || "").trim();
                  if (!text) continue;
                  text = text.replace(/\\bFollow\\b/gi, "").replace(/\\bReply\\b/gi, "").trim();
                  if (text.length > best.length) best = text;
                }
                caption = best;
              }
            }

            const timeEl = Array.from(document.querySelectorAll('time[datetime]')).find(visible);
            return {
              url: window.location.href,
              datetime: timeEl ? timeEl.getAttribute('datetime') || "" : "",
              caption,
              authors,
            };
        }"""
    )
    caption_text = _compact(str(data.get("caption") or ""))
    authors = [author for author in data.get("authors") or [] if author]
    current_path_handle = ""
    parsed = urlparse(page.url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 3 and path_parts[1] in {"p", "reel"}:
        current_path_handle = path_parts[0]
    ignored_handles = {
        canonical_handle(blogger_handle),
        canonical_handle(current_path_handle),
        *(canonical_handle(author) for author in authors),
    }
    mentioned = []
    for handle in HANDLE_RE.findall(caption_text):
        normalized = canonical_handle(handle)
        if not normalized or normalized in ignored_handles:
            continue
        if normalized not in {canonical_handle(item) for item in mentioned}:
            mentioned.append(handle)

    ad_likelihood, ad_reasoning = classify_ad_likelihood(caption_text, mentioned)
    date_iso = str(data.get("datetime") or "")
    post_date = None
    if date_iso:
        try:
            post_date = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        except ValueError:
            post_date = None

    return PostSnapshot(
        post_url=page.url,
        post_date=post_date,
        post_date_iso=post_date.isoformat() if post_date else date_iso,
        authors=authors,
        caption_text=caption_text,
        candidate_handles=mentioned,
        ad_likelihood=ad_likelihood,
        ad_reasoning=ad_reasoning,
    )


def classify_ad_likelihood(caption_text: str, candidate_handles: list[str]) -> tuple[str, str]:
    text = (caption_text or "").lower()
    score = 0
    reasons: list[str] = []
    if candidate_handles:
        score += 2
        reasons.append("есть явное @упоминание")
    for keyword in AD_KEYWORDS:
        if keyword in text:
            score += 1
            reasons.append(f"ключевое слово: {keyword}")
    if len(candidate_handles) >= 2:
        score += 1
        reasons.append("несколько @упоминаний")
    if score >= 4:
        return "high", "; ".join(reasons[:4]) or "сильные признаки рекламной интеграции"
    if score >= 2:
        return "medium", "; ".join(reasons[:4]) or "есть признаки интеграции"
    return "low", "; ".join(reasons[:4]) or "прямых признаков рекламы мало"


async def go_to_next_post(page: Page, human: Humanizer, logger: logging.Logger) -> bool:
    buttons = page.locator("button")
    count = await buttons.count()
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    preferred: tuple[Locator, float] | None = None
    best: tuple[Locator, float] | None = None
    for index in range(count):
        button = buttons.nth(index)
        try:
            if not await button.is_visible():
                continue
            aria = (_compact(await button.get_attribute("aria-label") or "")).lower()
            icon = button.locator('svg[aria-label="Next"], title')
            icon_text = _compact((await button.inner_text()) or "")
            has_next = False
            if await icon.count():
                icon_html = ((await button.inner_html()) or "").lower()
                has_next = 'aria-label="next"' in icon_html or ">next<" in icon_html
            if not has_next and "next" not in icon_text.lower() and aria != "next":
                continue
            box = await button.bounding_box()
            if not box:
                continue
            if box["x"] > viewport["width"] + 60:
                continue
            if aria == "next" and box["x"] >= viewport["width"] * 0.55:
                if preferred is None or box["x"] > preferred[1]:
                    preferred = (button, box["x"])
            if best is None or box["x"] > best[1]:
                best = (button, box["x"])
        except Exception:
            continue
    target = preferred or best
    if target is None:
        return False
    logger.info("Moving to next post in modal")
    current_shortcode = extract_shortcode(page.url)
    strategies = (
        ("human click", lambda: human.human_click(target[0])),
        ("force click", lambda: target[0].click(force=True)),
        ("dom click", lambda: target[0].evaluate("(el) => el.click()")),
    )
    for label, action in strategies:
        logger.info("Trying next-post navigation via %s", label)
        await action()
        deadline = datetime.now(timezone.utc) + timedelta(seconds=8)
        while datetime.now(timezone.utc) < deadline:
            next_shortcode = extract_shortcode(page.url)
            if next_shortcode and next_shortcode != current_shortcode:
                await human.pause(650, 1200)
                return True
            await human.pause(250, 500)
    return False


async def open_brand_profile_tab(
    context: BrowserContext,
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    *,
    handle: str,
    screenshots_dir: Path,
    source_blogger_handle: str,
    source_post: PostSnapshot,
) -> BrandAssessment:
    profile_url = f"https://www.instagram.com/{handle}/"
    brand_page = await context.new_page()
    screenshot_name = f"{source_blogger_handle}_{handle}_{extract_shortcode(source_post.post_url) or 'post'}.png"
    screenshot_path = screenshots_dir / screenshot_name
    try:
        await brand_page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        await human.pause(1100, 1800)
        brand_human = Humanizer(brand_page, settings=human.settings)
        await dismiss_instagram_popups(brand_page, brand_human, logger)

        async def safe_meta_content(selector: str) -> str:
            locator = brand_page.locator(selector).first
            try:
                if await locator.count():
                    return (await locator.get_attribute("content", timeout=5000)) or ""
            except Exception:
                return ""
            return ""

        meta_title = await safe_meta_content('meta[property="og:title"]')
        meta_description = await safe_meta_content('meta[name="description"]')
        header_text = ""
        header = brand_page.locator("header").first
        if await header.count():
            try:
                header_text = _compact(await header.inner_text(timeout=5000))
            except Exception:
                header_text = ""

        external_link = ""
        if await header.count():
            links = header.locator('a[href^="http"]')
            link_count = await links.count()
            for index in range(link_count):
                try:
                    href = await links.nth(index).get_attribute("href", timeout=3000)
                except Exception:
                    href = ""
                if href and "instagram.com" not in href and "threads.com" not in href:
                    external_link = href
                    break

        display_name = ""
        title_match = re.match(r"^(.*?)\s+\(@([A-Za-z0-9._]+)\)", meta_title or "")
        if title_match:
            display_name = _compact(title_match.group(1))
        followers_text = meta_description or ""
        bio = meta_description or header_text or _compact(await brand_page.title())
        category_label = ""
        header_lower = header_text.lower()
        for keyword in BRAND_KEYWORDS:
            if keyword in header_lower:
                category_label = keyword
                break

        brand_likelihood, confidence, reasoning, is_brand, niche, account_kind, outreach_fit = classify_brand_profile(
            handle=handle,
            display_name=display_name,
            bio=bio,
            category_label=category_label,
            external_link=external_link,
        )
        await capture_screenshot(brand_page, screenshot_path, logger)

        return BrandAssessment(
            handle=handle,
            profile_url=profile_url,
            is_brand=is_brand,
            account_kind=account_kind,
            outreach_fit=outreach_fit,
            brand_likelihood=brand_likelihood,
            ad_likelihood=source_post.ad_likelihood,
            niche=niche,
            confidence=confidence,
            reasoning=reasoning,
            display_name=display_name,
            bio=bio,
            category_label=category_label,
            followers_text=followers_text,
            external_link=external_link,
            screenshot_path=str(screenshot_path),
            source_posts=[source_post.post_url],
        )
    finally:
        try:
            await brand_page.close()
        except Exception:
            pass


def classify_brand_profile(
    *,
    handle: str,
    display_name: str,
    bio: str,
    category_label: str,
    external_link: str,
) -> tuple[str, str, str, bool, str, str, str]:
    haystack = _compact(" ".join([handle, display_name, bio, category_label])).lower()
    score = 0
    reasons: list[str] = []
    niche = ""
    account_kind = "unclear"

    if external_link:
        score += 2
        reasons.append("???? ??????? ??????")
    for keyword in BRAND_KEYWORDS:
        if keyword in haystack:
            score += 1
            reasons.append(f"brand-keyword: {keyword}")
            if not niche:
                niche = keyword
    if any(keyword in haystack for keyword in ("denim", "wear", "boutique", "collection", "atelier")):
        niche = "fashion"
    elif any(keyword in haystack for keyword in ("beauty", "cosmetic", "cosmetics", "??????", "????")):
        niche = "beauty"
    elif any(keyword in haystack for keyword in ("nutrition", "supplement", "fit", "sport", "?????", "???????")):
        niche = "sports_nutrition"
    elif any(keyword in haystack for keyword in ("flower", "flowers", "????")):
        niche = "flowers"

    has_brand_keywords = any(keyword in haystack for keyword in BRAND_KEYWORDS)
    has_person_keywords = any(keyword in haystack for keyword in PERSON_KEYWORDS)
    has_service_keywords = any(keyword in haystack for keyword in SERVICE_KEYWORDS)
    has_project_keywords = any(keyword in haystack for keyword in PROJECT_KEYWORDS)

    if has_project_keywords:
        account_kind = "project_media"
    elif has_brand_keywords and not has_person_keywords:
        account_kind = "brand_store"
    elif has_service_keywords:
        account_kind = "service_provider"
    elif has_person_keywords:
        account_kind = "personal_creator"

    if has_person_keywords:
        score -= 2
        reasons.append("???????? ??? ?????? ??????? ??? ??????????")
    if re.fullmatch(r"[a-z]+[._]?[a-z]+[._]?[a-z0-9]*", handle.lower()) and score == 0:
        reasons.append("handle ??? ?? ???? ???????????")

    if account_kind == "brand_store":
        outreach_fit = "high" if score >= 2 else "medium"
    elif account_kind == "service_provider":
        outreach_fit = "medium"
    elif account_kind == "project_media":
        outreach_fit = "low"
    else:
        outreach_fit = "low"

    is_brand = account_kind in {"brand_store", "service_provider"}
    if not external_link and has_person_keywords and not has_brand_keywords and not has_service_keywords:
        return "low", "low", "; ".join(reasons[:4]) or "??????? ?????? ????? ?? ??????", False, niche, account_kind, outreach_fit

    if score >= 4:
        return "high", "high", "; ".join(reasons[:4]) or "??????? ????? ?? ?????", is_brand, niche, account_kind, outreach_fit
    if score >= 2:
        return "medium", "medium", "; ".join(reasons[:4]) or "???? ???????? ????????????? ????????", is_brand, niche, account_kind, outreach_fit
    return "low", "low", "; ".join(reasons[:4]) or "??????? ?????? ????? ?? ??????", is_brand and outreach_fit != "low", niche, account_kind, outreach_fit


def upsert_brand_record(
    state: InstagramBrandSearchState,
    assessment: BrandAssessment,
    candidate: MentionCandidate,
) -> None:
    key = assessment.handle.lower()
    existing = state.brand_records.get(key)
    record = asdict(assessment)
    source_entry = {
        "blogger_handle": candidate.blogger_handle,
        "post_url": candidate.source_post_url,
        "post_date_iso": candidate.source_post_date_iso,
        "ad_likelihood": candidate.ad_likelihood,
        "ad_reasoning": candidate.ad_reasoning,
        "caption_excerpt": candidate.visible_context[:220],
    }
    if existing is None:
        record["sources"] = [source_entry]
        state.brand_records[key] = record
        return

    sources = existing.setdefault("sources", [])
    if source_entry not in sources:
        sources.append(source_entry)
    if assessment.screenshot_path:
        existing["screenshot_path"] = assessment.screenshot_path
    if assessment.external_link and not existing.get("external_link"):
        existing["external_link"] = assessment.external_link
    if assessment.account_kind and (existing.get("account_kind") in {"", "unclear", None}):
        existing["account_kind"] = assessment.account_kind
    if assessment.outreach_fit and assessment.outreach_fit != "low":
        existing["outreach_fit"] = assessment.outreach_fit
    if assessment.bio and len(assessment.bio) > len(existing.get("bio") or ""):
        existing["bio"] = assessment.bio
    if assessment.brand_likelihood == "high":
        existing["brand_likelihood"] = "high"
        existing["is_brand"] = existing.get("is_brand") or assessment.is_brand
    if assessment.ad_likelihood == "high":
        existing["ad_likelihood"] = "high"


def append_existing_brand_source(state: InstagramBrandSearchState, handle: str, candidate: MentionCandidate) -> None:
    existing = state.brand_records.get(handle.lower())
    if existing is None:
        return
    source_entry = {
        "blogger_handle": candidate.blogger_handle,
        "post_url": candidate.source_post_url,
        "post_date_iso": candidate.source_post_date_iso,
        "ad_likelihood": candidate.ad_likelihood,
        "ad_reasoning": candidate.ad_reasoning,
        "caption_excerpt": candidate.visible_context[:220],
    }
    sources = existing.setdefault("sources", [])
    if source_entry not in sources:
        sources.append(source_entry)
    source_posts = existing.setdefault("source_posts", [])
    if candidate.source_post_url and candidate.source_post_url not in source_posts:
        source_posts.append(candidate.source_post_url)


def update_blogger_stats(
    state: InstagramBrandSearchState,
    blogger_url: str,
    blogger_handle: str,
    *,
    scanned_increment: int = 0,
    candidate_increment: int = 0,
    accepted_handle: str = "",
    stopped_due_to_date: bool = False,
) -> None:
    stats = state.blogger_stats.setdefault(
        blogger_url,
        asdict(BloggerRunStats(profile_url=blogger_url, handle=blogger_handle)),
    )
    stats["handle"] = blogger_handle
    stats["scanned_posts"] = int(stats.get("scanned_posts", 0)) + scanned_increment
    stats["candidate_mentions"] = int(stats.get("candidate_mentions", 0)) + candidate_increment
    accepted = stats.setdefault("accepted_brand_handles", [])
    if accepted_handle and accepted_handle not in accepted:
        accepted.append(accepted_handle)
    if stopped_due_to_date:
        stats["stopped_due_to_date"] = True


def write_markdown_outputs(job: dict, state: InstagramBrandSearchState) -> None:
    outputs = job["outputs"]
    blogger_summary_path = Path(outputs["blogger_summary_md"])
    brand_links_path = Path(outputs["discovered_brand_links_md"])
    brand_dossiers_path = Path(outputs["extracted_candidates_md"])
    for path in (blogger_summary_path, brand_links_path, brand_dossiers_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    blogger_lines = ["# Blogger Summary", ""]
    for blogger_url, stats in sorted(state.blogger_stats.items()):
        blogger_handle = stats.get("handle") or extract_handle_from_url(blogger_url)
        accepted_handles = sorted(
            handle
            for handle, record in state.brand_records.items()
            if (record.get("outreach_fit", "low") != "low" or record.get("account_kind") in {"brand_store", "service_provider"})
            and any(source.get("blogger_handle") == blogger_handle for source in record.get("sources", []))
        )
        blogger_lines.extend(
            [
                f"## {blogger_handle}",
                f"- Profile: {md_link('@' + blogger_handle, blogger_url)}",
                f"- Scanned posts: {stats.get('scanned_posts', 0)}",
                f"- Candidate mentions: {stats.get('candidate_mentions', 0)}",
                f"- Accepted brand-like handles: {', '.join(accepted_handles) or 'none'}",
                f"- Stopped due to 1y cutoff: {'yes' if stats.get('stopped_due_to_date') else 'no'}",
                "",
            ]
        )
    blogger_summary_path.write_text("\n".join(blogger_lines).strip() + "\n", encoding="utf-8-sig")

    link_lines = ["# Brand Links", ""]
    for handle, record in sorted(state.brand_records.items()):
        if record.get("outreach_fit", "low") == "low" and record.get("account_kind") not in {"brand_store", "service_provider"}:
            continue
        screenshot_target = relative_markdown_target(brand_links_path, record.get("screenshot_path", ""))
        latest_source = ""
        if record.get("sources"):
            latest_source = record["sources"][-1].get("post_url", "")
        link_lines.extend(
            [
                f"## @{handle}",
                f"- Profile: {md_link('@' + handle, record.get('profile_url', ''))}",
                f"- Screenshot: {md_link('open screenshot', screenshot_target) if screenshot_target else ''}".rstrip(),
                f"- Account kind: {record.get('account_kind', '')}",
                f"- Outreach fit: {record.get('outreach_fit', '')}",
                f"- Brand likelihood: {record.get('brand_likelihood')}",
                f"- Ad likelihood: {record.get('ad_likelihood')}",
                f"- Sources: {len(record.get('sources', []))}",
                f"- Latest source post: {md_link('open post', latest_source) if latest_source else ''}".rstrip(),
                "",
            ]
        )
    brand_links_path.write_text("\n".join(link_lines).strip() + "\n", encoding="utf-8-sig")

    dossier_lines = ["# Brand Dossiers", ""]
    for handle, record in sorted(state.brand_records.items()):
        screenshot_target = relative_markdown_target(brand_dossiers_path, record.get("screenshot_path", ""))
        bio = normalize_text(record.get("bio", ""))
        reasoning = normalize_text(record.get("reasoning", ""))
        display_name = normalize_text(record.get("display_name", ""))
        dossier_lines.extend(
            [
                f"## @{handle}",
                f"- Profile: {md_link('@' + handle, record.get('profile_url', ''))}",
                f"- Screenshot: {md_link('open screenshot', screenshot_target) if screenshot_target else ''}".rstrip(),
                f"- Brand likelihood: {record.get('brand_likelihood', '')}",
                f"- Ad likelihood: {record.get('ad_likelihood', '')}",
                f"- Is brand: {'yes' if record.get('is_brand') else 'no'}",
                f"- Account kind: {record.get('account_kind', '')}",
                f"- Outreach fit: {record.get('outreach_fit', '')}",
                f"- Display name: {display_name}",
                f"- Niche: {record.get('niche', '')}",
                f"- Category label: {record.get('category_label', '')}",
                f"- External link: {md_link('open external link', record.get('external_link', '')) if record.get('external_link') else ''}".rstrip(),
                f"- Reasoning: {reasoning}",
                "",
                "### Bio",
                bio or "none",
                "",
                "### Source Posts",
            ]
        )
        sources = record.get("sources", [])
        if not sources:
            dossier_lines.append("- none")
        else:
            for source in sources:
                post_url = source.get("post_url", "")
                excerpt = normalize_text(source.get("caption_excerpt", ""))
                dossier_lines.append(
                    f"- {source.get('blogger_handle', '')} | {source.get('post_date_iso', '')} | {md_link('post', post_url) if post_url else ''} | ad={source.get('ad_likelihood', '')} | {normalize_text(source.get('ad_reasoning', ''))}"
                )
                if excerpt:
                    dossier_lines.append(f"  excerpt: {excerpt}")
        dossier_lines.append("")
    brand_dossiers_path.write_text("\n".join(dossier_lines).strip() + "\n", encoding="utf-8-sig")


def is_post_older_than_window(post_date: datetime | None, target_days: int) -> bool:
    if post_date is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=target_days)
    current = post_date.astimezone(timezone.utc) if post_date.tzinfo else post_date.replace(tzinfo=timezone.utc)
    return current < cutoff


def update_current_post_pointer(state: InstagramBrandSearchState, blogger_url: str, post_url: str) -> None:
    checkpoint = state.checkpoint_for(blogger_url)
    checkpoint.current_post_url = post_url
    checkpoint.last_processed_shortcode = extract_shortcode(post_url)
    checkpoint.current_post_date_iso = ""
    state.current_post_url = post_url
    state.current_post_date_iso = ""


async def process_current_post(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    state: InstagramBrandSearchState,
    job: dict,
    screenshots_dir: Path,
    blogger_url: str,
    blogger_handle: str,
) -> tuple[str, list[BrandAssessment]]:
    checkpoint = state.checkpoint_for(blogger_url)
    snapshot = await read_post_snapshot(page, blogger_handle)
    state.current_post_url = snapshot.post_url
    state.current_post_date_iso = snapshot.post_date_iso
    checkpoint.current_post_url = snapshot.post_url
    checkpoint.current_post_date_iso = snapshot.post_date_iso
    checkpoint.last_processed_shortcode = extract_shortcode(snapshot.post_url)

    if is_post_older_than_window(snapshot.post_date, job["scan_policy"]["target_period_days"]):
        existing_scanned = int(state.blogger_stats.get(blogger_url, {}).get("scanned_posts", 0))
        if existing_scanned > 0:
            update_blogger_stats(state, blogger_url, blogger_handle, stopped_due_to_date=True)
            return "stop", []
        return "skip_old", []

    if snapshot.post_url not in checkpoint.processed_post_urls:
        checkpoint.processed_post_urls.append(snapshot.post_url)
    checkpoint.processed_posts_count += 1
    update_blogger_stats(
        state,
        blogger_url,
        blogger_handle,
        scanned_increment=1,
        candidate_increment=len(snapshot.candidate_handles),
    )

    assessments: list[BrandAssessment] = []
    for handle in snapshot.candidate_handles[: job["scan_policy"].get("max_candidates_per_post", 10)]:
        key = candidate_key(snapshot.post_url, handle)
        if key in checkpoint.processed_candidate_keys:
            continue
        checkpoint.processed_candidate_keys.append(key)
        candidate = MentionCandidate(
            blogger_handle=blogger_handle,
            source_post_url=snapshot.post_url,
            source_post_date_iso=snapshot.post_date_iso,
            source_authors=snapshot.authors,
            candidate_handle=handle,
            visible_context=snapshot.caption_text,
            caption_text=snapshot.caption_text,
            source_type="caption",
            ad_likelihood=snapshot.ad_likelihood,
            ad_reasoning=snapshot.ad_reasoning,
        )
        existing = state.brand_records.get(handle.lower())
        if existing is not None:
            logger.info("Skipping duplicate known handle @%s on %s", handle, snapshot.post_url)
            append_existing_brand_source(state, handle, candidate)
            continue
        try:
            assessment = await open_brand_profile_tab(
                page.context,
                page,
                human,
                logger,
                handle=handle,
                screenshots_dir=screenshots_dir,
                source_blogger_handle=blogger_handle,
                source_post=snapshot,
            )
        except Exception as exc:
            logger.info("Brand tab failed for @%s on %s: %s", handle, snapshot.post_url, exc)
            await page.bring_to_front()
            await human.pause(450, 850)
            continue
        upsert_brand_record(state, assessment, candidate)
        if assessment.is_brand:
            update_blogger_stats(state, blogger_url, blogger_handle, accepted_handle=handle)
        assessments.append(assessment)
        await page.bring_to_front()
        await human.pause(450, 850)

    return "continue", assessments


async def recover_modal_if_needed(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    state: InstagramBrandSearchState,
    blogger_url: str,
) -> Page:
    checkpoint = state.checkpoint_for(blogger_url)
    current_shortcode = extract_shortcode(page.url)
    target_shortcode = extract_shortcode(checkpoint.current_post_url or state.current_post_url)
    if target_shortcode and current_shortcode != target_shortcode:
        logger.info("Recovering modal state for %s", checkpoint.current_post_url)
        return await reopen_post_modal(page, human, logger, blogger_url, checkpoint.current_post_url)
    return page


async def run_blogger_scan(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    state: InstagramBrandSearchState,
    job: dict,
    state_path: Path,
    screenshots_dir: Path,
    blogger: BloggerTarget,
) -> Page:
    checkpoint = state.checkpoint_for(blogger.profile_url)
    state.current_blogger_url = blogger.profile_url
    await ensure_profile_page(page, human, logger, blogger.profile_url)
    blogger_handle = extract_handle_from_url(blogger.profile_url)

    if checkpoint.current_post_url:
        page = await reopen_post_modal(page, human, logger, blogger.profile_url, checkpoint.current_post_url)
    else:
        page = await open_profile_post_from_grid(page, human, logger)
    update_current_post_pointer(state, blogger.profile_url, page.url)

    fallback_limit = int(job["scan_policy"]["fallback_max_posts_per_blogger"])
    while checkpoint.processed_posts_count < fallback_limit:
        page = await recover_modal_if_needed(page, human, logger, state, blogger.profile_url)
        update_current_post_pointer(state, blogger.profile_url, page.url)
        action, _ = await process_current_post(
            page,
            human,
            logger,
            state,
            job,
            screenshots_dir,
            blogger.profile_url,
            blogger_handle,
        )
        state.save(state_path)
        write_markdown_outputs(job, state)
        if action == "stop":
            break
        if action == "skip_old":
            moved = await go_to_next_post(page, human, logger)
            if moved:
                update_current_post_pointer(state, blogger.profile_url, page.url)
                state.save(state_path)
                write_markdown_outputs(job, state)
            else:
                logger.info("No further Next button found for blogger %s while skipping old pinned content", blogger_handle)
                break
            continue
        moved = await go_to_next_post(page, human, logger)
        if moved:
            update_current_post_pointer(state, blogger.profile_url, page.url)
            state.save(state_path)
            write_markdown_outputs(job, state)
        else:
            logger.info("No further Next button found for blogger %s", blogger_handle)
            break

    state.mark_blogger_completed(blogger.profile_url)
    state.save(state_path)
    write_markdown_outputs(job, state)
    return page


async def run_instagram_brand_search(
    page: Page,
    human: Humanizer,
    logger: logging.Logger,
    state: InstagramBrandSearchState,
    job: dict,
    *,
    state_path: Path,
) -> None:
    screenshots_dir = Path(job["outputs"]["candidate_screenshots_dir"])
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    targets = load_blogger_targets(Path(job["inputs"]["blogger_list_file"]))
    if state.current_blogger_url:
        start_index = next(
            (index for index, target in enumerate(targets) if target.profile_url == state.current_blogger_url),
            0,
        )
        targets = targets[start_index:] + targets[:start_index]

    for blogger in targets:
        if blogger.profile_url in state.completed_bloggers:
            continue
        logger.info("Scanning blogger %s", blogger.profile_url)
        page = await run_blogger_scan(page, human, logger, state, job, state_path, screenshots_dir, blogger)
        state.save(state_path)
        write_markdown_outputs(job, state)

    write_markdown_outputs(job, state)
