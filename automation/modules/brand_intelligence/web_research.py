from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path
import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
MAX_FETCH_BYTES = 250_000
SEARCH_LIMIT = 5
FETCH_PAGE_LIMIT = 4
SOCIAL_DOMAINS = (
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "pinterest.com",
)
REVIEW_DOMAINS = (
    "trustpilot.com",
    "otzovik.com",
    "irecommend.ru",
    "tripadvisor.com",
    "sitejabber.com",
)
CONTACT_KEYWORDS = ("contact", "contacts", "email", "support", "customer service", "press", "partnership", "wholesale")
NEGATIVE_KEYWORDS = (
    "scam",
    "fraud",
    "lawsuit",
    "complaint",
    "bad review",
    "terrible",
    "fake",
    "refund",
    "problem",
    "мошен",
    "жалоб",
    "обман",
    "плох",
    "ужас",
    "поддел",
    "скандал",
    "претенз",
    "суд",
)
POSITIVE_KEYWORDS = (
    "official",
    "premium",
    "luxury",
    "best",
    "trusted",
    "delivery",
    "boutique",
    "award",
    "официаль",
    "преми",
    "люкс",
    "доставк",
    "бутик",
    "надеж",
    "качеств",
)
PRICE_PREMIUM_KEYWORDS = (
    "luxury",
    "premium",
    "exclusive",
    "designer",
    "high jewelry",
    "haute",
    "fine jewelry",
    "люкс",
    "преми",
    "эксклюзив",
    "дизайнер",
    "ювелир",
    "бутик",
)
PRICE_MASS_KEYWORDS = (
    "sale",
    "discount",
    "marketplace",
    "cheap",
    "affordable",
    "budget",
    "скидк",
    "распродаж",
    "дешев",
    "бюджет",
    "маркетплейс",
)
RUSSIA_KEYWORDS = ("russia", "moscow", "st petersburg", ".ru", "росси", "москва", "петербург", "спб")


@dataclass
class SearchResult:
    title: str
    url: str
    display_url: str = ""
    snippet: str = ""


@dataclass
class PageSummary:
    url: str
    title: str = ""
    meta_description: str = ""
    excerpt: str = ""
    fetched: bool = False
    error: str = ""


@dataclass
class WebResearchReport:
    search_queries: list[str] = field(default_factory=list)
    search_results: list[SearchResult] = field(default_factory=list)
    page_summaries: list[PageSummary] = field(default_factory=list)
    official_site_found: bool = False
    review_source_count: int = 0
    negative_signal_count: int = 0
    positive_signal_count: int = 0
    tone: str = "neutral"
    geo: str = "unknown"
    price_segment: str = "unknown"
    summary_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["search_results"] = [asdict(item) for item in self.search_results]
        payload["page_summaries"] = [asdict(item) for item in self.page_summaries]
        return payload


def _ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _compact(text: str) -> str:
    return " ".join(unescape((text or "").replace("\xa0", " ")).split())


def _strip_tags(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return _compact(text)


def _fetch_text(url: str, *, max_bytes: int = MAX_FETCH_BYTES) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as response:
        payload = response.read(max_bytes)
    return payload.decode("utf-8", "ignore")


def _decode_duckduckgo_redirect(raw_href: str) -> str:
    href = raw_href.strip()
    if href.startswith("//"):
        href = "https:" + href
    if "duckduckgo.com/l/?" not in href:
        return href
    parsed = urllib.parse.urlparse(href)
    query = urllib.parse.parse_qs(parsed.query)
    target = query.get("uddg", [""])[0]
    return urllib.parse.unquote(target) if target else href


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _is_social_url(url: str) -> bool:
    domain = _domain(url)
    return any(domain == item or domain.endswith(f".{item}") for item in SOCIAL_DOMAINS)


def _is_review_url(url: str) -> bool:
    domain = _domain(url)
    return any(domain == item or domain.endswith(f".{item}") for item in REVIEW_DOMAINS)


def _tokenize_brand(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in re.findall(r"[a-zA-Z0-9а-яА-Я]{3,}", value or ""):
            lowered = token.lower()
            if lowered not in {"and", "the", "official", "brand"}:
                tokens.add(lowered)
    return tokens


def _looks_like_official_result(item: SearchResult, brand_tokens: set[str]) -> bool:
    domain = _domain(item.url)
    if not domain or _is_social_url(item.url) or _is_review_url(item.url):
        return False
    combined = f"{item.title} {item.snippet} {item.display_url}".lower()
    if "official" in combined or "официаль" in combined:
        return True
    domain_tokens = set(re.findall(r"[a-z0-9а-я]{3,}", domain))
    return any(token in domain_tokens for token in brand_tokens if len(token) >= 4)


def _search_rank(item: SearchResult, brand_tokens: set[str]) -> tuple[int, int, int]:
    score = 0
    combined = f"{item.title} {item.snippet}".lower()
    if not _is_social_url(item.url):
        score += 5
    if _looks_like_official_result(item, brand_tokens):
        score += 4
    if _is_review_url(item.url):
        score += 3
    if _contains_any(combined, ("review", "reviews", "отзыв", "отзывы")):
        score += 2
    if _contains_any(combined, ("official", "официаль")):
        score += 2
    domain = _domain(item.url)
    if any(token in domain for token in brand_tokens if len(token) >= 4):
        score += 2
    return (score, 0 if _is_social_url(item.url) else 1, 1 if _is_review_url(item.url) else 0)


def search_duckduckgo_lite(query: str, *, limit: int = SEARCH_LIMIT) -> list[SearchResult]:
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query)
    html = _fetch_text(url)
    anchor_re = re.compile(
        r"<a[^>]+href=\"?(?P<href>//duckduckgo\.com/l/\?uddg=[^\"'> ]+|https?://[^\"'> ]+)\"?[^>]*class=['\"]result-link['\"][^>]*>(?P<title>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    results: list[SearchResult] = []
    matches = list(anchor_re.finditer(html))
    for index, match in enumerate(matches[:limit]):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(html)
        block = html[start:end]
        snippet_match = re.search(r"<td class=['\"]result-snippet['\"]>(?P<snippet>.*?)</td>", block, re.IGNORECASE | re.DOTALL)
        link_text_match = re.search(r"<span class=['\"]link-text['\"]>(?P<link_text>.*?)</span>", block, re.IGNORECASE | re.DOTALL)
        results.append(
            SearchResult(
                title=_strip_tags(match.group("title")),
                url=_decode_duckduckgo_redirect(match.group("href")),
                display_url=_strip_tags(link_text_match.group("link_text")) if link_text_match else "",
                snippet=_strip_tags(snippet_match.group("snippet")) if snippet_match else "",
            )
        )
    return results


def search_bing_rss(query: str, *, limit: int = SEARCH_LIMIT) -> list[SearchResult]:
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    xml_text = _fetch_text(url)
    root = ET.fromstring(xml_text)
    results: list[SearchResult] = []
    for item in root.findall("./channel/item"):
        title = _compact(item.findtext("title") or "")
        link = _compact(item.findtext("link") or "")
        description = _compact(item.findtext("description") or "")
        if not link:
            continue
        results.append(
            SearchResult(
                title=title,
                url=link,
                display_url=_domain(link),
                snippet=description,
            )
        )
        if len(results) >= limit:
            break
    return results


def summarize_page(url: str) -> PageSummary:
    try:
        html = _fetch_text(url)
    except Exception as exc:
        return PageSummary(url=url, fetched=False, error=str(exc))

    title_match = re.search(r"(?is)<title>(.*?)</title>", html)
    meta_match = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']|<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
        html,
    )
    body_text = _strip_tags(html)
    excerpt = body_text[:600]
    meta_description = ""
    if meta_match:
        meta_description = _compact(meta_match.group(1) or meta_match.group(2) or "")
    return PageSummary(
        url=url,
        title=_compact(title_match.group(1)) if title_match else "",
        meta_description=meta_description,
        excerpt=excerpt,
        fetched=True,
    )


def _infer_price_segment(text: str) -> str:
    if _contains_any(text, PRICE_PREMIUM_KEYWORDS):
        return "premium"
    if _contains_any(text, PRICE_MASS_KEYWORDS):
        return "mass"
    return "unknown"


def _infer_geo(text: str) -> str:
    return "russia" if _contains_any(text, RUSSIA_KEYWORDS) else "unknown"


def run_brand_web_research(snapshot: dict) -> WebResearchReport:
    handle = str(snapshot.get("handle", "") or "").strip()
    display_name = str(snapshot.get("display_name", "") or "").strip()
    external_link = str(snapshot.get("external_link", "") or "").strip()
    brand_tokens = _tokenize_brand(handle.replace("_", " "), display_name)

    queries = [
        f"\"{display_name or handle}\" official site -site:instagram.com -site:facebook.com -site:tiktok.com -site:x.com",
        f"\"{display_name or handle}\" reviews -site:instagram.com -site:facebook.com -site:tiktok.com -site:x.com",
        f"\"{display_name or handle}\" trustpilot OR review",
        f"\"{display_name or handle}\" contact email -site:instagram.com -site:facebook.com -site:tiktok.com -site:x.com",
        f"\"{handle}\" brand",
    ]

    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    for query in queries:
        try:
            provider_results = search_bing_rss(query, limit=SEARCH_LIMIT)
        except Exception:
            provider_results = search_duckduckgo_lite(query, limit=SEARCH_LIMIT)
        for item in provider_results:
            normalized_url = _normalize_url(item.url)
            if not normalized_url or normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            results.append(
                SearchResult(
                    title=item.title,
                    url=normalized_url,
                    display_url=item.display_url or _domain(normalized_url),
                    snippet=item.snippet,
                )
            )
            if len(results) >= SEARCH_LIMIT * 2:
                break
        if len(results) >= SEARCH_LIMIT * 2:
            break
    results = sorted(results, key=lambda item: _search_rank(item, brand_tokens), reverse=True)[:SEARCH_LIMIT]

    page_urls: list[str] = []
    normalized_external = _normalize_url(external_link) if external_link else ""
    if normalized_external:
        page_urls.append(normalized_external)
    for result in results:
        if _is_social_url(result.url):
            continue
        if result.url not in page_urls:
            page_urls.append(result.url)
        if len(page_urls) >= FETCH_PAGE_LIMIT:
            break
    if not page_urls:
        for result in results:
            if result.url not in page_urls:
                page_urls.append(result.url)
            if len(page_urls) >= FETCH_PAGE_LIMIT:
                break
    page_summaries = [summarize_page(page_url) for page_url in page_urls[:FETCH_PAGE_LIMIT]]

    combined = "\n".join(
        [
            display_name,
            handle,
            external_link,
            *[f"{item.title} {item.snippet} {item.display_url}" for item in results],
            *[f"{item.title} {item.meta_description} {item.excerpt}" for item in page_summaries],
        ]
    )
    lowered = combined.lower()
    negative_signal_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in lowered)
    positive_signal_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in lowered)
    review_source_count = sum(
        1
        for item in results
        if _is_review_url(item.url) or _contains_any(f"{item.title} {item.snippet} {item.display_url}", ("review", "reviews", "отзыв", "отзывы"))
    )

    tone = "neutral"
    if negative_signal_count > positive_signal_count + 1:
        tone = "negative"
    elif positive_signal_count > negative_signal_count:
        tone = "positive"
    elif negative_signal_count or positive_signal_count:
        tone = "mixed"

    official_site_found = bool(normalized_external and not _is_social_url(normalized_external)) or any(
        _looks_like_official_result(item, brand_tokens) for item in results
    )
    geo = _infer_geo(lowered)
    price_segment = _infer_price_segment(lowered)

    notes = [
        f"Collected {len(results)} ranked search results and {len(page_summaries)} fetched pages.",
        f"Non-social search results kept: {sum(1 for item in results if not _is_social_url(item.url))}.",
    ]
    if review_source_count:
        notes.append(f"Found {review_source_count} review-oriented search results.")
    if official_site_found:
        notes.append("Detected an official site signal or external brand link.")
    if negative_signal_count:
        notes.append(f"Detected {negative_signal_count} negative/risk lexical signals.")
    if positive_signal_count:
        notes.append(f"Detected {positive_signal_count} positive/commercial lexical signals.")

    return WebResearchReport(
        search_queries=queries,
        search_results=results,
        page_summaries=page_summaries,
        official_site_found=official_site_found,
        review_source_count=review_source_count,
        negative_signal_count=negative_signal_count,
        positive_signal_count=positive_signal_count,
        tone=tone,
        geo=geo,
        price_segment=price_segment,
        summary_notes=notes,
    )


def write_research_report(path: Path, report: WebResearchReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
