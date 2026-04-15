"""Parse The Blueprint career feeds and employer archive into structured company seeds."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import re
import time
import urllib.parse

import yaml

from ..web_research import extract_emails_from_text, extract_phones_from_text, fetch_urllib_html


DEFAULT_BLUEPRINT_PAGE_IDS = (
    39253,
    39231,
    39208,
    39174,
    39136,
    39123,
    39083,
    39025,
    39022,
    39020,
    38963,
    38962,
    38937,
    38916,
    38898,
    38884,
    38838,
    38839,
    38824,
    38823,
    38826,
    38813,
)

BLUEPRINT_CAREER_BASE_URL = "https://theblueprint.ru/career"

ARTICLE_RE = re.compile(
    r'<article class="feed-item" data-post-id="(?P<post_id>\d+)" data-url="(?P<path>[^"]+)" data-title="(?P<title>.*?)">(?P<body>.*?)</article>',
    re.DOTALL,
)
BRAND_LINK_RE = re.compile(
    r'<li[^>]+data-name="(?P<name>.*?)"[^>]*>\s*<a href="(?P<href>/career/brand/(?P<slug>[^"]+))">',
    re.IGNORECASE | re.DOTALL,
)
DESC_RE = re.compile(r'<div class="desc">\s*(?P<body>.*?)\s*</div>', re.DOTALL)
JSON_LD_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"(?is)<(script|style).*?>.*?</\1>|<[^>]+>")
MARKETING_SIGNAL_RE = re.compile(
    r"\b(marketing|pr|smm|brand|content|creative|editor|редактор|маркет|бренд|контент|креатив|коммуникац|спецпроект|партнерств)\b",
    re.IGNORECASE,
)


@dataclass
class BlueprintBrand:
    name: str = ""
    slug: str = ""
    url: str = ""


@dataclass
class BlueprintCareerListing:
    company_name: str = ""
    role_title: str = ""
    description: str = ""
    article_title: str = ""
    date_posted: str = ""
    page_id: int = 0
    post_id: int = 0
    source_url: str = ""
    source_page_url: str = ""
    source_feed_kind: str = "page"
    source_feed_key: str = ""
    brand_slug: str = ""
    brand_name_hint: str = ""
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    marketing_signal: bool = False


def _compact(text: str) -> str:
    return " ".join(unescape((text or "").replace("\xa0", " ")).split())


def _strip_tags(text: str) -> str:
    return _compact(TAG_RE.sub(" ", text or ""))


def _decode_js_text(value: str) -> str:
    text = str(value or "")
    if "\\" not in text:
        return _compact(text)

    decoded = text.replace("\\/", "/").replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")
    if "\\u" in decoded or "\\x" in decoded:
        try:
            decoded = decoded.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            pass
    return _compact(decoded)


def _normalize_page_html(html: str) -> str:
    return html.replace("\\/", "/").replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")


def _normalize_key(value: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", " ", str(value or "").casefold()).strip()


def _fetch_html_with_retries(url: str, *, attempts: int = 3, sleep_seconds: float = 0.4) -> str:
    for attempt in range(attempts):
        html = fetch_urllib_html(url, max_bytes=2_500_000) or ""
        if html and len(html) > 1000:
            return html
        if attempt + 1 < attempts:
            time.sleep(sleep_seconds)
    return ""


def _extract_job_postings(raw_html: str) -> list[dict]:
    normalized_html = _normalize_page_html(raw_html)
    postings: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for match in JSON_LD_RE.finditer(normalized_html):
        payload = match.group("body").strip()
        if not payload:
            continue

        job_type = re.search(r'"@type"\s*:\s*"(?P<value>.*?)"', payload, re.DOTALL)
        if str(job_type.group("value") if job_type else "").casefold() != "jobposting":
            continue

        organization_name_match = re.search(
            r'"hiringOrganization"\s*:\s*\{.*?"name"\s*:\s*"(?P<value>.*?)"',
            payload,
            re.DOTALL,
        )
        role_title_match = re.search(r'"title"\s*:\s*"(?P<value>.*?)"', payload, re.DOTALL)
        description_match = re.search(r'"description"\s*:\s*"(?P<value>.*?)"', payload, re.DOTALL)
        date_posted_match = re.search(r'"datePosted"\s*:\s*"(?P<value>.*?)"', payload, re.DOTALL)

        organization_name = _decode_js_text(organization_name_match.group("value") if organization_name_match else "")
        role_title = _decode_js_text(role_title_match.group("value") if role_title_match else "")
        description = _strip_tags(_decode_js_text(description_match.group("value") if description_match else ""))
        date_posted = _compact(date_posted_match.group("value") if date_posted_match else "")

        if not organization_name and not role_title:
            continue
        key = (organization_name, role_title, date_posted)
        if key in seen:
            continue
        seen.add(key)
        postings.append(
            {
                "company_name": organization_name,
                "role_title": role_title,
                "description": description,
                "date_posted": date_posted,
            }
        )
    return postings


def _score_job_posting(article_title: str, description: str, posting: dict) -> int:
    article_norm = _normalize_key(article_title)
    desc_norm = _normalize_key(description)
    company_norm = _normalize_key(str(posting.get("company_name") or ""))
    role_norm = _normalize_key(str(posting.get("role_title") or ""))

    score = 0
    if company_norm and company_norm in article_norm:
        score += 5
    if company_norm and company_norm in desc_norm:
        score += 4
    if role_norm and role_norm in article_norm:
        score += 3
    if role_norm and role_norm in desc_norm:
        score += 2
    return score


def _match_job_posting(
    article_title: str,
    description: str,
    postings: list[dict],
    used_indices: set[int],
) -> dict:
    best_index = -1
    best_score = -1

    for index, posting in enumerate(postings):
        if index in used_indices:
            continue
        score = _score_job_posting(article_title, description, posting)
        if score > best_score:
            best_index = index
            best_score = score

    if best_index >= 0 and best_score > 0:
        used_indices.add(best_index)
        return postings[best_index]

    return {}


def _parse_feed_page(
    raw_html: str,
    *,
    source_page_url: str,
    source_feed_kind: str,
    source_feed_key: str,
    page_id: int = 0,
    brand_slug: str = "",
    brand_name_hint: str = "",
) -> list[BlueprintCareerListing]:
    if not raw_html:
        return []

    normalized_html = _normalize_page_html(raw_html)
    postings = _extract_job_postings(raw_html)
    used_postings: set[int] = set()
    listings: list[BlueprintCareerListing] = []

    for match in ARTICLE_RE.finditer(normalized_html):
        description_html = ""
        desc_match = DESC_RE.search(match.group("body") or "")
        if desc_match:
            description_html = desc_match.group("body")

        article_title = _decode_js_text(match.group("title"))
        description = _strip_tags(_decode_js_text(description_html))
        posting = _match_job_posting(article_title, description, postings, used_postings)

        source_path = _decode_js_text(match.group("path"))
        source_url = urllib.parse.urljoin("https://theblueprint.ru", source_path)
        company_name = _compact(str(posting.get("company_name") or brand_name_hint or article_title))
        role_title = _compact(str(posting.get("role_title") or ""))
        marketing_signal = bool(MARKETING_SIGNAL_RE.search(f"{role_title} {description}"))

        listings.append(
            BlueprintCareerListing(
                company_name=company_name,
                role_title=role_title,
                description=description,
                article_title=article_title,
                date_posted=str(posting.get("date_posted") or ""),
                page_id=page_id,
                post_id=int(match.group("post_id")),
                source_url=source_url,
                source_page_url=source_page_url,
                source_feed_kind=source_feed_kind,
                source_feed_key=source_feed_key,
                brand_slug=brand_slug,
                brand_name_hint=brand_name_hint,
                emails=extract_emails_from_text(description),
                phones=extract_phones_from_text(description),
                marketing_signal=marketing_signal,
            )
        )

    return listings


def fetch_blueprint_career_page(page_id: int) -> str:
    """Fetch one The Blueprint article page as raw HTML."""
    return _fetch_html_with_retries(f"{BLUEPRINT_CAREER_BASE_URL}/{int(page_id)}")


def parse_blueprint_career_page(page_id: int, raw_html: str) -> list[BlueprintCareerListing]:
    """Parse one seed career page into listing-level records."""
    return _parse_feed_page(
        raw_html,
        source_page_url=f"{BLUEPRINT_CAREER_BASE_URL}/{int(page_id)}",
        source_feed_kind="page",
        source_feed_key=str(int(page_id)),
        page_id=int(page_id),
    )


def fetch_blueprint_brand_index() -> str:
    """Fetch the main career index page containing the full employer directory."""
    return _fetch_html_with_retries(BLUEPRINT_CAREER_BASE_URL)


def parse_blueprint_brand_index(raw_html: str) -> list[BlueprintBrand]:
    """Extract all employer brand pages from the left-column career directory."""
    normalized_html = _normalize_page_html(raw_html)
    brands: list[BlueprintBrand] = []
    seen_slugs: set[str] = set()

    for match in BRAND_LINK_RE.finditer(normalized_html):
        slug = _compact(match.group("slug"))
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        href = _compact(match.group("href"))
        brands.append(
            BlueprintBrand(
                name=_decode_js_text(match.group("name")),
                slug=slug,
                url=urllib.parse.urljoin("https://theblueprint.ru", href),
            )
        )

    brands.sort(key=lambda item: item.name.casefold())
    return brands


def fetch_blueprint_brand_page(brand_slug: str) -> str:
    """Fetch one employer archive page under /career/brand/<slug>."""
    return _fetch_html_with_retries(f"{BLUEPRINT_CAREER_BASE_URL}/brand/{brand_slug.strip('/')}")


def parse_blueprint_brand_page(brand: BlueprintBrand, raw_html: str) -> list[BlueprintCareerListing]:
    """Parse one employer archive page into listing-level records."""
    return _parse_feed_page(
        raw_html,
        source_page_url=brand.url,
        source_feed_kind="brand",
        source_feed_key=brand.slug,
        brand_slug=brand.slug,
        brand_name_hint=brand.name,
    )


def aggregate_blueprint_companies(listings: list[BlueprintCareerListing]) -> list[dict]:
    """Aggregate listing-level rows into company seeds for manual review."""
    by_company: dict[str, dict] = {}

    for listing in listings:
        company_name = listing.company_name or listing.brand_name_hint or listing.article_title
        company_key = _normalize_key(company_name) or str(listing.post_id)
        record = by_company.setdefault(
            company_key,
            {
                "name": company_name,
                "entity_type": "prospect",
                "segment": "",
                "industry": "",
                "source": "theblueprint_career",
                "contacts": {"emails": [], "phones": []},
                "hiring": [],
                "blueprint_page_ids": [],
                "blueprint_brand_slugs": [],
                "blueprint_brand_urls": [],
                "blueprint_urls": [],
                "marketing_signal": False,
                "parser_notes": [
                    "Auto-parsed from The Blueprint career feed.",
                    "Requires manual segment and nsx_fit review before enrichment.",
                ],
            },
        )

        if listing.page_id and listing.page_id not in record["blueprint_page_ids"]:
            record["blueprint_page_ids"].append(listing.page_id)
        if listing.brand_slug and listing.brand_slug not in record["blueprint_brand_slugs"]:
            record["blueprint_brand_slugs"].append(listing.brand_slug)
        if listing.source_feed_kind == "brand" and listing.source_page_url and listing.source_page_url not in record["blueprint_brand_urls"]:
            record["blueprint_brand_urls"].append(listing.source_page_url)
        if listing.source_url and listing.source_url not in record["blueprint_urls"]:
            record["blueprint_urls"].append(listing.source_url)
        record["marketing_signal"] = bool(record["marketing_signal"] or listing.marketing_signal)

        for email in listing.emails:
            if email not in record["contacts"]["emails"]:
                record["contacts"]["emails"].append(email)
        for phone in listing.phones:
            if phone not in record["contacts"]["phones"]:
                record["contacts"]["phones"].append(phone)

        hiring_item = {
            "role": listing.role_title,
            "published_at": listing.date_posted,
            "source_url": listing.source_url,
            "source_page_url": listing.source_page_url,
            "source_feed_kind": listing.source_feed_kind,
            "source_feed_key": listing.source_feed_key,
            "marketing_signal": listing.marketing_signal,
        }
        if hiring_item not in record["hiring"]:
            record["hiring"].append(hiring_item)

    companies = list(by_company.values())
    companies.sort(key=lambda item: (-sum(1 for role in item["hiring"] if role["marketing_signal"]), item["name"].casefold()))
    return companies


def build_blueprint_career_export(page_ids: list[int]) -> dict:
    """Fetch, parse, and aggregate a batch of seed article pages."""
    listings: list[BlueprintCareerListing] = []
    errors: list[str] = []

    for page_id in page_ids:
        raw_html = fetch_blueprint_career_page(page_id)
        if not raw_html:
            errors.append(f"page {page_id}: fetch failed")
            continue
        parsed = parse_blueprint_career_page(page_id, raw_html)
        if not parsed:
            errors.append(f"page {page_id}: no listings parsed")
            continue
        listings.extend(parsed)

    companies = aggregate_blueprint_companies(listings)
    return {
        "source": BLUEPRINT_CAREER_BASE_URL,
        "discovery_mode": "seed_pages",
        "page_ids": page_ids,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "listing_count": len(listings),
        "company_count": len(companies),
        "errors": errors,
        "companies": companies,
    }


def build_blueprint_brand_export(
    *,
    brand_slugs: list[str] | None = None,
    brand_limit: int | None = None,
    max_workers: int = 8,
) -> dict:
    """Fetch the employer directory, crawl brand pages, and aggregate the full archive."""
    index_html = fetch_blueprint_brand_index()
    if not index_html:
        return {
            "source": BLUEPRINT_CAREER_BASE_URL,
            "discovery_mode": "brand_index",
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "brand_catalog_count": 0,
            "brands_crawled_count": 0,
            "article_page_count": 0,
            "listing_count": 0,
            "company_count": 0,
            "errors": ["brand index fetch failed"],
            "brands": [],
            "article_page_ids": [],
            "companies": [],
        }

    catalog = parse_blueprint_brand_index(index_html)
    catalog_total = len(catalog)
    errors: list[str] = []
    empty_brand_slugs: list[str] = []

    if brand_slugs:
        wanted = {slug.strip().casefold() for slug in brand_slugs if slug.strip()}
        catalog = [brand for brand in catalog if brand.slug.casefold() in wanted]

    if brand_limit is not None:
        catalog = catalog[: max(brand_limit, 0)]

    listings: list[BlueprintCareerListing] = []

    def _crawl_brand(brand: BlueprintBrand) -> tuple[BlueprintBrand, list[BlueprintCareerListing], str]:
        html = fetch_blueprint_brand_page(brand.slug)
        if not html:
            return brand, [], "fetch failed"
        parsed = parse_blueprint_brand_page(brand, html)
        if not parsed:
            return brand, [], "no listings parsed"
        return brand, parsed, ""

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {executor.submit(_crawl_brand, brand): brand for brand in catalog}
        for future in as_completed(futures):
            brand, parsed, error = future.result()
            if error:
                if error == "no listings parsed":
                    empty_brand_slugs.append(brand.slug)
                errors.append(f"brand {brand.slug}: {error}")
                continue
            listings.extend(parsed)

    companies = aggregate_blueprint_companies(listings)
    article_page_ids = sorted({listing.post_id for listing in listings if listing.post_id})
    crawled_brand_slugs = sorted({listing.brand_slug for listing in listings if listing.brand_slug})
    crawled_brands = [brand for brand in catalog if brand.slug in set(crawled_brand_slugs)]

    return {
        "source": BLUEPRINT_CAREER_BASE_URL,
        "discovery_mode": "brand_index",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "brand_catalog_count": catalog_total,
        "brand_selection_count": len(catalog),
        "brands_crawled_count": len(crawled_brands),
        "empty_brand_pages_count": len(empty_brand_slugs),
        "article_page_count": len(article_page_ids),
        "listing_count": len(listings),
        "company_count": len(companies),
        "errors": errors,
        "brand_catalog": [asdict(brand) for brand in catalog],
        "brands": [asdict(brand) for brand in crawled_brands],
        "empty_brand_slugs": sorted(empty_brand_slugs),
        "article_page_ids": article_page_ids,
        "companies": companies,
    }


def write_blueprint_career_export(path: Path, payload: dict) -> None:
    """Persist parser output as UTF-8 YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def listings_as_dicts(listings: list[BlueprintCareerListing]) -> list[dict]:
    return [asdict(item) for item in listings]
