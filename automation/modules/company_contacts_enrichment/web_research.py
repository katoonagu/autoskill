"""Web fetching layer with Firecrawl -> WebFetch -> Playwright fallback chain.

This module provides a unified interface for fetching web content.
Priority order:
  1. Firecrawl CLI (best quality, JS rendering, clean markdown)
  2. urllib (stdlib, no JS, but free and unlimited)
  3. Playwright via AdsPower (for sites requiring login or anti-bot bypass)
"""

from __future__ import annotations

from html import unescape
from pathlib import Path
import json
import re
import ssl
import subprocess
import urllib.parse
import urllib.request


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
MAX_FETCH_BYTES = 500_000
FIRECRAWL_TIMEOUT = 30


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


# ---------------------------------------------------------------------------
# Fetcher 1: Firecrawl CLI
# ---------------------------------------------------------------------------

def fetch_firecrawl(url: str, *, timeout: int = FIRECRAWL_TIMEOUT) -> str | None:
    """Fetch a page via Firecrawl CLI.  Returns markdown or None on failure."""
    try:
        result = subprocess.run(
            ["npx", "-y", "firecrawl", "scrape", url, "--format", "markdown"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def search_firecrawl(query: str, *, limit: int = 5) -> list[dict] | None:
    """Search via Firecrawl CLI.  Returns list of {title, url, snippet} or None."""
    try:
        result = subprocess.run(
            ["npx", "-y", "firecrawl", "search", query, "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=FIRECRAWL_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return list(data["data"])
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Fetcher 2: stdlib urllib (no JS rendering)
# ---------------------------------------------------------------------------

def fetch_urllib(url: str, *, max_bytes: int = MAX_FETCH_BYTES) -> str | None:
    """Fetch raw HTML via urllib.  Returns stripped text or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            html = resp.read(max_bytes).decode("utf-8", "ignore")
        return _strip_tags(html)
    except Exception:
        return None


def fetch_urllib_html(url: str, *, max_bytes: int = MAX_FETCH_BYTES) -> str | None:
    """Fetch raw HTML (with tags) via urllib."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            return resp.read(max_bytes).decode("utf-8", "ignore")
    except Exception:
        return None


def search_bing_rss(query: str, *, limit: int = 5) -> list[dict]:
    """Search via Bing RSS feed (free, no API key)."""
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            xml_text = resp.read(MAX_FETCH_BYTES).decode("utf-8", "ignore")
    except Exception:
        return []

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []
    for item in root.findall("./channel/item"):
        title = _compact(item.findtext("title") or "")
        link = _compact(item.findtext("link") or "")
        description = _compact(item.findtext("description") or "")
        if link:
            results.append({"title": title, "url": link, "snippet": description})
        if len(results) >= limit:
            break
    return results


def search_duckduckgo(query: str, *, limit: int = 5) -> list[dict]:
    """Search via DuckDuckGo lite (fallback for Bing)."""
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query)
    try:
        html = fetch_urllib_html(url) or ""
    except Exception:
        return []

    anchor_re = re.compile(
        r"<a[^>]+href=\"?(?P<href>//duckduckgo\.com/l/\?uddg=[^\"'> ]+|https?://[^\"'> ]+)\"?[^>]*class=['\"]result-link['\"][^>]*>(?P<title>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    results = []
    for match in anchor_re.finditer(html):
        href = match.group("href").strip()
        if href.startswith("//"):
            href = "https:" + href
        if "duckduckgo.com/l/?" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get("uddg", [""])[0]
            href = urllib.parse.unquote(target) if target else href
        results.append({
            "title": _strip_tags(match.group("title")),
            "url": href,
            "snippet": "",
        })
        if len(results) >= limit:
            break
    return results


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

def smart_fetch(url: str, *, use_firecrawl: bool = True) -> str:
    """Fetch page content with automatic fallback.

    Returns clean text content.  Empty string on total failure.
    """
    if use_firecrawl:
        content = fetch_firecrawl(url)
        if content:
            return content

    content = fetch_urllib(url)
    if content:
        return content

    return ""


def smart_search(query: str, *, limit: int = 5, use_firecrawl: bool = True) -> list[dict]:
    """Search with automatic fallback.

    Returns list of {title, url, snippet}.
    """
    if use_firecrawl:
        results = search_firecrawl(query, limit=limit)
        if results:
            return results

    results = search_bing_rss(query, limit=limit)
    if results:
        return results

    return search_duckduckgo(query, limit=limit)


def extract_emails_from_text(text: str) -> list[str]:
    """Extract unique email addresses from text."""
    pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    seen: set[str] = set()
    result: list[str] = []
    for match in pattern.finditer(text):
        email = match.group(0).lower()
        if email not in seen:
            seen.add(email)
            result.append(email)
    return result


def extract_phones_from_text(text: str) -> list[str]:
    """Extract and normalize phone numbers from text."""
    pattern = re.compile(r"(?<!\w)(?:\+?\d[\d\-\s\(\)]{7,}\d)")
    seen: set[str] = set()
    result: list[str] = []
    for match in pattern.finditer(text):
        digits = re.sub(r"\D+", "", match.group(0))
        if len(digits) < 7 or len(digits) > 15:
            continue
        normalized = ("+" + digits) if match.group(0).strip().startswith("+") else digits
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_telegrams_from_text(text: str) -> list[str]:
    """Extract Telegram links from text."""
    pattern = re.compile(r"https?://t\.me/[A-Za-z0-9_]+", re.IGNORECASE)
    return list(dict.fromkeys(m.group(0) for m in pattern.finditer(text)))


def domain_from_url(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urllib.parse.urlparse(str(url or "").strip())
        return parsed.netloc.lower().removeprefix("www.")
    except Exception:
        return ""
