"""
Downloads the HTML of a source page.

Two strategies:

  1. requests + BeautifulSoup  - the default, used for every source.
  2. Playwright                - only for sources flagged `js_required`, i.e.
                                 pages that build their event list in the
                                 browser and therefore return an empty shell
                                 to a plain HTTP request.

If Playwright is not installed the JavaScript sources are skipped quietly
instead of breaking the whole crawl.
"""

import time

import requests

from config import settings
from utils.logger import get_logger

log = get_logger("fetcher")

# A single session reuses TCP connections across all sources - much faster.
_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": settings.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
)


def fetch_static(url):
    """Fetch a page with requests. Returns HTML text, or None on failure."""
    for attempt in range(settings.MAX_RETRIES + 1):
        try:
            response = _session.get(
                url, timeout=settings.REQUEST_TIMEOUT, allow_redirects=True
            )
            if response.status_code == 200:
                # requests falls back to ISO-8859-1 when a server does not
                # declare a charset in its Content-Type header, which turns
                # UTF-8 smart quotes / em-dashes into mojibake ("Kerala's"
                # becomes "Keralaâ€™s"). None of the sites we
                # crawl actually serve Latin-1; trust the content sniffing
                # instead whenever the header did not specify an encoding.
                if response.encoding is None or "charset" not in (
                    response.headers.get("Content-Type", "")
                ):
                    response.encoding = response.apparent_encoding
                return response.text
            log.warning("HTTP %s for %s", response.status_code, url)
            # 4xx will not fix itself on retry; give up immediately.
            if 400 <= response.status_code < 500:
                return None
        except requests.RequestException as exc:
            log.warning("Request failed (%s/%s) for %s: %s",
                        attempt + 1, settings.MAX_RETRIES + 1, url, exc)
        # Linear back-off between retries.
        time.sleep(settings.REQUEST_DELAY * (attempt + 1))
    return None


def fetch_dynamic(url):
    """
    Fetch a JavaScript-rendered page with Playwright.

    Returns the rendered HTML, or None when Playwright is unavailable or the
    page fails to load.
    """
    if not settings.ENABLE_PLAYWRIGHT:
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.info("Playwright not installed - skipping JS source %s", url)
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=settings.USER_AGENT)
            page.goto(url, timeout=settings.REQUEST_TIMEOUT * 1000,
                      wait_until="domcontentloaded")
            # Give client-side rendering a moment to paint the event list.
            page.wait_for_timeout(settings.PLAYWRIGHT_WAIT_MS)
            html = page.content()
            browser.close()
            return html
    except Exception as exc:                      # noqa: BLE001 - never break the crawl
        log.warning("Playwright failed for %s: %s", url, exc)
        return None


def fetch(source):
    """
    Fetch one source dictionary from config/sources.py.

    BeautifulSoup-friendly HTML is always preferred; Playwright is the
    fallback only where it is genuinely required.
    """
    url = source["url"]

    if source.get("js_required"):
        html = fetch_dynamic(url)
        if html:
            return html
        # A JS site may still ship server-rendered content - worth one try.
        return fetch_static(url)

    html = fetch_static(url)
    if html and len(html) > 500:
        return html

    # Static fetch came back empty or suspiciously small: the page probably
    # needs a browser after all.
    log.info("Static fetch thin for %s - trying Playwright", url)
    return fetch_dynamic(url) or html


def fetch_url(url, js_required=False):
    """
    Fetch an arbitrary URL directly (not tied to a config/sources.py entry).

    Used by the Learning Programs adapters, which crawl individual course /
    scheme pages discovered at runtime rather than a fixed list of sources.
    """
    return fetch({"url": url, "js_required": js_required})
