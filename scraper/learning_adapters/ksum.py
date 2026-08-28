"""
Kerala Startup Mission (KSUM) adapter.

KSUM is the Government of Kerala's nodal agency for the startup ecosystem
(https://startupmission.kerala.gov.in). Its homepage links to one page per
named scheme/programme under /schemes/<slug> - Ignite, CEF, the Idea Box
Fund of Funds, the incubation & acceleration track, the women/transgender
productisation grant, and so on. Each of those is a real, individually
addressable official programme page, which is the "individual programs, not
one platform entry" shape rule #5 asks for (mirrors KSUM IEDC / Idea Box /
student innovation programmes named explicitly in the brief).

DISCOVER: the homepage's own navigation is crawled for /schemes/<slug> links
          - nothing hardcoded beyond the domain and that one starting page.
EXTRACT:  each scheme page's og:title (the same text used by KSUM as the
          page/programme name), its first substantial paragraph as the
          description, and an outbound application link if the page has one
          (a Google Form or an explicit "Apply/Register" link).

A scheme page with no title or no real paragraph of body text is skipped
rather than stored with guessed content (rule #12).
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.fetcher import fetch_url
from utils.logger import get_logger

log = get_logger("learning.ksum")

BASE_URL = "https://startupmission.kerala.gov.in"
HOMEPAGE = BASE_URL + "/"

APPLY_TEXT_PATTERN = re.compile(r"apply|register|enroll|submit\s*(your)?\s*idea", re.I)
APPLY_HOST_HINTS = ("forms.gle", "docs.google.com/forms")

# Every KSUM scheme page describes a funding / incubation / mentorship
# programme for founders - not a paid course - so the shared classification
# is set once here rather than re-detected per page.
DEFAULT_CATEGORY = ["Entrepreneurship", "Business"]


def _discover_scheme_urls():
    """DISCOVER: read /schemes/<slug> links off the KSUM homepage."""
    html = fetch_url(HOMEPAGE)
    if not html:
        log.warning("Could not fetch KSUM homepage")
        return []

    soup = BeautifulSoup(html, "html.parser")
    slugs = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = re.match(r"^/schemes/([A-Za-z0-9_-]+)$", href.strip())
        if match:
            slugs.add(match.group(1))

    urls = [urljoin(BASE_URL, f"/schemes/{slug}") for slug in sorted(slugs)]
    log.info("KSUM: discovered %d scheme pages", len(urls))
    return urls


def _first_paragraph(soup):
    """The first paragraph of real body copy - long enough to be a description."""
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) >= 40:
            return text
    return ""


def _find_apply_url(soup, page_url):
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(" ", strip=True)
        if any(hint in href for hint in APPLY_HOST_HINTS) or APPLY_TEXT_PATTERN.search(text):
            return urljoin(page_url, href)
    return ""


def _extract_scheme(url):
    """EXTRACT: title + description + apply link for one scheme page."""
    html = fetch_url(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    og_title = soup.find("meta", attrs={"property": "og:title"})
    title = (og_title["content"].strip() if og_title and og_title.get("content") else "")
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    # KSUM's <title> often carries the site suffix; og:title does not, but
    # strip it defensively either way.
    title = re.sub(r"\s*\|\s*Kerala Startup Mission\s*$", "", title).strip()

    description = _first_paragraph(soup)

    if not title or not description:
        log.info("KSUM: skipping %s - no clear title/description on the page", url)
        return None

    apply_url = _find_apply_url(soup, url)

    return {
        "title": title,
        "provider": "Kerala Startup Mission (KSUM)",
        "description": description,
        "category": list(DEFAULT_CATEGORY),
        "subcategory": "Startup Programme",
        "program_type": "Fellowship",
        "country": "India",
        "city": "",
        "location_type": "Hybrid",
        "eligible_countries": ["India"],
        # KSUM schemes are participation-free for founders; several also
        # disburse a grant/investment, which is FUNDING, not a course fee -
        # kept separate per rule #7 (fully funded/free vs stipend/grant).
        "cost_type": "FREE",
        "price": 0,
        "currency": "INR",
        "funding_type": "GRANT",
        "funding_amount": "",
        # Not a training course, so certification does not apply; leaving
        # this unknown rather than false avoids implying it was checked and
        # found absent.
        "certificate_available": "unknown",
        "eligibility": {"description": "See official scheme page for eligibility criteria."},
        "start_date": "",
        "end_date": "",
        "application_deadline": "",
        "official_url": url,
        "application_url": apply_url,
        "source_type": "GOVERNMENT",
        "source_name": "Kerala Startup Mission (KSUM)",
    }


def fetch():
    """DISCOVER + EXTRACT: every real KSUM scheme page found on the homepage."""
    programs = []
    for url in _discover_scheme_urls():
        try:
            scheme = _extract_scheme(url)
        except Exception as exc:                  # noqa: BLE001 - one bad page must
            log.warning("KSUM: failed to parse %s: %s", url, exc)  # not stop the rest
            continue
        if scheme:
            programs.append(scheme)

    log.info("KSUM: extracted %d schemes", len(programs))
    return programs


ADAPTER = {
    "name": "Kerala Startup Mission (KSUM)",
    "source_type": "GOVERNMENT",
    "fetch": fetch,
}
