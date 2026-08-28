"""
Turns one page of HTML into a list of event dictionaries.

Because the fifty-odd source websites share no common markup, the extractor
uses three strategies in order of reliability:

  1. JSON-LD  - many modern sites embed schema.org "Event" objects. When they
                do, we get perfect data with no guessing at all.
  2. Cards    - repeated blocks whose class names mention event/card/listing.
                This is how most event listing pages are built.
  3. Links    - last resort: scan every <a> whose URL or text looks like an
                event, and read the date from its surrounding text.

Every candidate is then cleaned, categorised and de-noised before it leaves
this module.
"""

import hashlib
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import settings
from config.course_filter import course_reason, is_course
from scraper import classifier
from scraper.dateparser import extract_date, parse_date_string
from utils.logger import get_logger

log = get_logger("extractor")

# URL fragments that usually indicate an event / programme page.
EVENT_URL_HINTS = [
    "event", "events", "conference", "summit", "expo", "webinar", "workshop",
    "hackathon", "meetup", "jam", "session", "programme", "program", "grant",
    "funding", "scheme", "challenge", "apply", "register", "bootcamp",
    "demo-day", "cohort", "fellowship", "news",
]

# Class-name fragments that usually wrap a single event card.
CARD_CLASS_HINTS = re.compile(
    r"event|card|listing|tile|item|post|entry|teaser|result|program|grid-item",
    re.I,
)


def make_fingerprint(source_name, title, date_iso):
    """
    Build the duplicate-detection key.

    The title is lower-cased and stripped of punctuation first, so
    "AI Summit 2026" and "AI Summit, 2026!" collapse to the same fingerprint
    and the event is stored only once.
    """
    normalised = re.sub(r"[^a-z0-9]+", "", title.lower())
    raw = f"{source_name.lower()}|{normalised}|{date_iso or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Strategy 1 - schema.org JSON-LD
# ---------------------------------------------------------------------------

def _flatten_jsonld(data):
    """Yield every dictionary inside a JSON-LD blob, however deeply nested."""
    if isinstance(data, dict):
        if "@graph" in data:
            for item in _flatten_jsonld(data["@graph"]):
                yield item
        yield data
        for value in data.values():
            if isinstance(value, (dict, list)):
                for item in _flatten_jsonld(value):
                    yield item
    elif isinstance(data, list):
        for entry in data:
            for item in _flatten_jsonld(entry):
                yield item


def extract_from_jsonld(soup, source):
    """Read schema.org Event objects embedded in <script type=ld+json>."""
    events = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        for node in _flatten_jsonld(data):
            if not isinstance(node, dict):
                continue

            node_type = node.get("@type", "")
            if isinstance(node_type, list):
                node_type = " ".join(node_type)
            if "event" not in str(node_type).lower():
                continue

            title = classifier.clean_title(str(node.get("name", "")))
            if not title:
                continue

            # Date - schema.org gives us a clean ISO string.
            raw_date, iso_date = parse_date_string(str(node.get("startDate", ""))[:10])

            # Location can be a string or a nested Place object.
            location = ""
            place = node.get("location")
            if isinstance(place, dict):
                location = str(place.get("name", ""))
                address = place.get("address")
                if isinstance(address, dict):
                    location = (
                        address.get("addressLocality")
                        or address.get("addressRegion")
                        or address.get("addressCountry")
                        or location
                    )
                elif isinstance(address, str):
                    location = address or location
            elif isinstance(place, str):
                location = place

            url = node.get("url") or node.get("mainEntityOfPage") or ""
            if isinstance(url, dict):
                url = url.get("@id", "")

            events.append(
                _build_event(
                    source=source,
                    title=title,
                    url=urljoin(source["url"], str(url)) if url else source["url"],
                    raw_date=raw_date,
                    iso_date=iso_date,
                    context_text=f"{title} {location} {node.get('description', '')}",
                    location_hint=classifier.clean_title(str(location)),
                )
            )

    return [e for e in events if e]


# ---------------------------------------------------------------------------
# Strategy 2 - repeated event cards
# ---------------------------------------------------------------------------

def extract_from_cards(soup, source):
    """Find repeated blocks that look like event cards and read each one."""
    events = []
    seen_titles = set()

    candidates = soup.find_all(
        ["article", "li", "div", "section"], attrs={"class": CARD_CLASS_HINTS}
    )

    # A candidate that wraps two or more *sibling* candidates is the list
    # container itself, not a single event - e.g. a div.events wrapping ten
    # div.event-row children. A card that just nests through one chain of
    # wrapper divs (card > card-body) is still a single event, so only each
    # candidate's *nearest* matched ancestor counts as its parent card.
    candidate_ids = {id(c) for c in candidates}
    nearest_matched_parent = {}
    for card in candidates:
        for ancestor in card.parents:
            if id(ancestor) in candidate_ids:
                nearest_matched_parent[id(card)] = id(ancestor)
                break

    direct_children_count = {}
    for parent_id in nearest_matched_parent.values():
        direct_children_count[parent_id] = direct_children_count.get(parent_id, 0) + 1

    wrapper_ids = {cid for cid, count in direct_children_count.items() if count >= 2}
    candidates = [c for c in candidates if id(c) not in wrapper_ids]

    kept_cards = []

    for card in candidates:
        text = card.get_text(" ", strip=True)

        # A card that contains an entire page's worth of text is a container,
        # not a single event.
        if not text or len(text) > 1200:
            continue

        # Cards matching the class hints often nest (a "card" wrapping a
        # "card-body"). find_all visits parents before children, so if this
        # card sits inside one we already kept, it is the same event with
        # less context (often missing the date) - skip it.
        if any(kept in card.parents for kept in kept_cards):
            continue

        # The title is the card's heading, or its most prominent link. A card
        # can carry several headings (e.g. a label like "Apply By" above the
        # real name) - prefer one classed as a title, otherwise the longest
        # heading text, since labels are short and names are not.
        headings = card.find_all(["h1", "h2", "h3", "h4", "h5"])
        heading = next(
            (h for h in headings if any("title" in c for c in h.get("class") or [])),
            None,
        )
        if not heading and headings:
            heading = max(headings, key=lambda h: len(h.get_text(strip=True)))
        title = classifier.clean_title(heading.get_text(" ", strip=True)) if heading else ""

        link_tag = card.find("a", href=True)
        if not title and link_tag:
            title = classifier.clean_title(link_tag.get_text(" ", strip=True))

        if not title or classifier.is_noise(title):
            continue

        raw_date, iso_date = extract_date(card, text)

        # A long block of text with neither a link to follow nor a date to
        # show is usually page furniture (an intro paragraph, a section
        # blurb) that only matched the class hints by coincidence, not a
        # real event. Short cards are kept even without a link or date -
        # some event widgets are plain text with routing handled elsewhere.
        if not link_tag and not iso_date and len(text) > 120:
            continue

        # Cards nest inside each other; keep the first occurrence only.
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        kept_cards.append(card)

        url = urljoin(source["url"], link_tag["href"]) if link_tag else source["url"]

        event = _build_event(
            source=source,
            title=title,
            url=url,
            raw_date=raw_date,
            iso_date=iso_date,
            context_text=text,
        )
        if event:
            events.append(event)

    return events


# ---------------------------------------------------------------------------
# Strategy 3 - bare links
# ---------------------------------------------------------------------------

def extract_from_links(soup, source):
    """
    Fallback for pages with no usable card markup (typical of government
    "what's new" pages, which are just long lists of links).
    """
    events = []
    seen_titles = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = classifier.clean_title(link.get_text(" ", strip=True))

        if not title or classifier.is_noise(title):
            continue

        key = title.lower()
        if key in seen_titles:
            continue

        # The link must either point at an event-ish URL or read like one.
        href_lower = href.lower()
        looks_like_event = any(hint in href_lower for hint in EVENT_URL_HINTS)
        if not looks_like_event and not classifier.is_relevant(title):
            continue

        # Read the date from the link's neighbourhood, not just its own text.
        container = link.find_parent(["li", "tr", "div", "article", "p"]) or link
        context = container.get_text(" ", strip=True)[:600]
        raw_date, iso_date = extract_date(container, context)

        event = _build_event(
            source=source,
            title=title,
            url=urljoin(source["url"], href),
            raw_date=raw_date,
            iso_date=iso_date,
            context_text=context or title,
            strict=True,          # weakest strategy - demand a date or a clear
        )                         # opportunity keyword before accepting
        if event:
            seen_titles.add(key)
            events.append(event)

    return events


# ---------------------------------------------------------------------------
# Shared record builder
# ---------------------------------------------------------------------------

def _build_event(source, title, url, raw_date, iso_date, context_text,
                 location_hint=None, strict=False):
    """
    Assemble one finished event dictionary, or return None if the candidate
    fails one of the quality checks.

    `strict` is set by the link-scanning strategy, which runs on pages with no
    real event markup (typically government "what's new" lists). There, a
    candidate must either carry a date or clearly name an opportunity.
    """
    haystack = f"{title} {context_text}"

    # The dashboard tracks opportunities, not courses. Rejecting here - the
    # one chokepoint every extraction strategy funnels through - keeps course
    # listings out of the database entirely rather than hiding them in the UI.
    if is_course(title, context_text):
        log.debug("Skipping course listing: %s (%s)",
                  title, course_reason(title, context_text))
        return None

    # Discard anything unrelated to our industries.
    if not classifier.is_relevant(haystack):
        return None

    # Drop news coverage of events that already took place.
    if classifier.is_past_report(title):
        return None

    # An undated candidate has to name an opportunity type, whichever strategy
    # found it. Card and JSON-LD markup leaks page furniture too ("Innovation
    # Zone", "What we offer"), and without this those arrive undated and
    # unusable. `strict` no longer changes the rule - it is kept so the
    # link-scanning caller reads the same - but the check now applies to every
    # strategy, which is what keeps purged fragments from coming back on the
    # next crawl.
    if not iso_date and not classifier.looks_like_opportunity(title):
        return None

    # Categorise from the title first - it is the most reliable signal. Only
    # when the title says nothing useful do we fall back to the surrounding
    # card text, which often mentions unrelated topics from neighbouring cards.
    category = classifier.detect_category(title, default="")
    if not category:
        category = classifier.detect_category(context_text, default=source["category"])
    location = location_hint or classifier.detect_location(haystack)
    if not location or location == "Not specified":
        # Fall back to the region declared for the source website.
        location = source.get("region") or "Not specified"
    mode = classifier.detect_mode(haystack, location)

    event = {
        "title": title,
        "category": category,
        # How close this is to games / AR-VR / apps; drives the ranking.
        "focus": classifier.focus_score(title, category, context_text),
        "location": location,
        "date": raw_date or "Date TBA",
        "date_iso": iso_date or "",
        "registration_url": url,
        "website": source["website"],
        "source": source["name"],
        "status": "Open",            # recalculated later from date_iso
        "mode": mode,
        "country": source.get("country", ""),
        "region": source.get("region", ""),
        "fingerprint": make_fingerprint(source["name"], title, iso_date),
    }

    return event


def extract_events(html, source):
    """
    Public entry point: HTML in, list of event dictionaries out.

    Strategies run in order and stop as soon as one produces a usable result,
    so a site with proper schema.org markup never falls through to guessing.
    """
    if not html:
        return []

    # html.parser is part of the standard library - no lxml dependency needed.
    soup = BeautifulSoup(html, "html.parser")

    # Strip elements that only ever contain noise.
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        # Keep JSON-LD scripts - they are read separately, before this runs.
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.decompose()

    results = extract_from_jsonld(BeautifulSoup(html, "html.parser"), source)
    if results:
        log.info("%s: %d events from JSON-LD", source["name"], len(results))
    else:
        results = extract_from_cards(soup, source)
        if results:
            log.info("%s: %d events from cards", source["name"], len(results))
        else:
            results = extract_from_links(soup, source)
            log.info("%s: %d events from links", source["name"], len(results))

    # Final de-duplication inside this one page.
    unique = {}
    for event in results:
        unique.setdefault(event["fingerprint"], event)

    return list(unique.values())[: settings.MAX_EVENTS_PER_SOURCE]
