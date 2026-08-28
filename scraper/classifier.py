"""
Turns raw scraped text into structured fields:

  * category   - one of the twelve dashboard categories
  * location   - city / venue / "Online"
  * mode       - Online or Offline
  * relevance  - is this event about our industries at all?

All rules are plain keyword matching, so nothing here costs money to run.
"""

import re

from config.categories import (
    CATEGORY_KEYWORDS,
    FOCUS_CATEGORIES,
    FOCUS_KEYWORDS,
    NOISE_KEYWORDS,
    PAST_REPORT_KEYWORDS,
    RELEVANCE_KEYWORDS,
    STRONG_EVENT_KEYWORDS,
)

# Cities that show up often in the sources we crawl. Detecting one gives the
# event a real location instead of "Not specified".
KNOWN_LOCATIONS = [
    # Kerala
    "Kochi", "Cochin", "Ernakulam", "Trivandrum", "Thiruvananthapuram",
    "Kozhikode", "Calicut", "Thrissur", "Kollam", "Kannur", "Kerala",
    # Rest of India
    "Bengaluru", "Bangalore", "Karnataka", "Hyderabad", "Chennai",
    "Tamil Nadu", "Coimbatore", "Madurai", "Mumbai", "Pune",
    "Delhi", "New Delhi", "Noida", "Gurugram", "Gurgaon", "Kolkata",
    "Ahmedabad", "Jaipur", "Indore", "Chandigarh", "Goa", "India",
    # Global
    "San Francisco", "Los Angeles", "Las Vegas", "New York", "Seattle",
    "Austin", "Boston", "London", "Berlin", "Cologne", "Munich", "Paris",
    "Amsterdam", "Barcelona", "Lisbon", "Dubai", "Abu Dhabi", "Singapore",
    "Tokyo", "Seoul", "Shanghai", "Sydney", "Toronto", "Vancouver",
    "USA", "UK", "Germany", "Japan", "Canada", "Australia", "UAE",
]

# Titles opening with one of these are product promotions, not events.
PROMO_OPENERS = (
    "get the ", "get started", "download ", "try the ", "try our ",
    "explore the ", "watch ", "read ", "discover the ", "introducing ",
    "meet the ", "buy ", "shop ", "browse ", "view the ", "see the ",
    "check out ", "sign up for our", "listen to ",
)

# Any of these in the text means the event happens on the internet.
ONLINE_HINTS = [
    "online", "virtual", "webinar", "livestream", "live stream", "remote",
    "zoom", "google meet", "ms teams", "microsoft teams", "youtube live",
    "anywhere", "worldwide (online)", "digital event",
]


# A calendar cell scraped as if it were an event. Listing pages built as
# month grids ("September 06", "Mon 12 Oct 2026") leak these, and they carry
# no opportunity at all.
_DATE_ONLY = re.compile(
    r"^(?:mon|tue|wed|thu|fri|sat|sun)?[a-z]*\s*[\d\s,./:-]*"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"[\s\d,./:-]*$",
    re.I,
)

# Section labels a scraper can mistake for a title. Unlike NOISE_KEYWORDS
# these only count when they are the *whole* title - "Conference activities"
# is noise, "IEEE Kerala Conference activities briefing" is not.
GENERIC_LABELS = {
    "conference activities", "event activities", "activities", "events",
    "programs", "programmes", "opportunities", "announcements", "news",
    "gallery", "highlights", "updates", "schedule", "agenda", "speakers",
    "sponsors", "partners", "registration", "our programs", "past editions",
}


def is_noise(title):
    """True for navigation links, footers and other non-event text."""
    if not title:
        return True

    cleaned = title.strip()

    # So long it is a paragraph rather than a title.
    if len(cleaned) > 180:
        return True

    # Short text is usually a nav link, but a few genuine events have very
    # short names ("TIGG Summit", "GameOn 2026"). Below 8 characters nothing
    # is worth keeping; between 8 and 12 the title has to name an opportunity
    # type or a year to survive.
    if len(cleaned) < 8:
        return True
    if len(cleaned) < 12 and not looks_like_opportunity(cleaned):
        return True

    lowered = cleaned.lower()

    # Boilerplate link text.
    for word in NOISE_KEYWORDS:
        if word in lowered:
            return True

    # Marketing call-to-action copy. "Get the Azure mobile app" and "Watch the
    # keynote" pass every other check - they are short, wordy and on-topic -
    # so they are caught by the verb they open with instead.
    for opener in PROMO_OPENERS:
        if lowered.startswith(opener):
            return True

    # Mostly punctuation / numbers rather than words. Acronym-plus-year names
    # ("IGDC 2026") fail the ratio on length alone, so a title that names an
    # opportunity type or a year is exempt - the date-only check below still
    # catches a bare "12 - 14 November 2026".
    letters = sum(ch.isalpha() for ch in cleaned)
    if letters < len(cleaned) * 0.5 and not looks_like_opportunity(cleaned):
        return True

    # Needs at least two words to be a title.
    if len(cleaned.split()) < 2:
        return True

    # Whatever else it contains, a title needs at least one real word.
    if not re.search(r"[A-Za-z]{3}", cleaned):
        return True

    # A list item scraped with its bullet number still attached ("1 Product
    # Launch Apply Now", "4 Investor Connect"), or a call-to-action button
    # caught as a title. Only a single leading digit counts, so real names
    # that open with a number survive ("10 Days of Code Hackathon", "2026
    # Startup Summit").
    if re.match(r"^\d\s+\D", cleaned):
        return True
    if re.search(r"(apply now|register here|book now|get your pass)\s*$",
                 lowered):
        return True

    # A bare date off a calendar grid, or a bare section label.
    if _DATE_ONLY.match(cleaned):
        return True
    if lowered.strip(" :-–—") in GENERIC_LABELS:
        return True

    return False


def _compile_keywords(keywords):
    """
    Build one word-boundary regex from a keyword list.

    Word boundaries matter: a plain substring search finds "unity" inside
    "Community" and "ai" inside "chair", which mis-files events badly. A
    trailing "s?" lets one keyword cover its plural ("game" matches "games").
    """
    parts = sorted({k.strip() for k in keywords if k.strip()}, key=len, reverse=True)
    pattern = "|".join(re.escape(part) for part in parts)
    return re.compile(r"\b(?:" + pattern + r")s?\b", re.I)


# Pre-compiled once at import time - the crawl runs these against thousands
# of strings, so re-compiling per call would be wasteful.
_CATEGORY_PATTERNS = [
    (category, _compile_keywords(keywords))
    for category, keywords in CATEGORY_KEYWORDS.items()
]
_RELEVANCE_PATTERN = _compile_keywords(RELEVANCE_KEYWORDS)
_STRONG_PATTERN = _compile_keywords(STRONG_EVENT_KEYWORDS)
_FOCUS_STRONG_PATTERN = _compile_keywords(FOCUS_KEYWORDS["strong"])
_FOCUS_WEAK_PATTERN = _compile_keywords(FOCUS_KEYWORDS["weak"])


def is_past_report(title):
    """
    True when the title reads like a news story about a finished event.

    "Workshop on DPDP Act organised in Leh" is a report; "DPDP Act Workshop -
    Register Now" is an opportunity. Only the second belongs on the dashboard.
    """
    lowered = title.lower()
    return any(word in lowered for word in PAST_REPORT_KEYWORDS)


def looks_like_opportunity(title):
    """
    True when the title names something a person could actually attend, join
    or apply to. Used to keep the weakest extraction strategy honest.
    """
    return bool(_STRONG_PATTERN.search(title))


def is_relevant(text):
    """
    True when the text mentions one of our industries or an event word.

    Whole-word matching keeps "ai" from firing on "chair" or "email".
    """
    return bool(_RELEVANCE_PATTERN.search(text))


def detect_category(text, default="Technology Event"):
    """
    Pick the best category for an event.

    CATEGORY_KEYWORDS is ordered from most specific (Hackathon, Funding) to
    most general, and the first match wins.
    """
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return default  # "" means "undecided" - the caller may try other text


def focus_score(title, category, context_text=""):
    """
    How close an event sits to what Rextech Studios actually builds:
    games, AR/VR experiences and apps.

        2  the title itself names one of those (a certain hit)
        1  the category is one of ours, or supporting words appear nearby
        0  everything else - still stored, just ranked below the rest

    The score drives the default ordering and the "Core focus" filter, so a
    game jam always outranks a generic cloud webinar.
    """
    if _FOCUS_STRONG_PATTERN.search(title):
        return 2

    in_focus_category = category in FOCUS_CATEGORIES

    # A strong word further down the card is good evidence, but only when the
    # categoriser agrees - otherwise one stray "app" in a sidebar promotes an
    # unrelated event.
    if in_focus_category and _FOCUS_STRONG_PATTERN.search(context_text or ""):
        return 2

    if in_focus_category:
        return 1

    if _FOCUS_WEAK_PATTERN.search(title):
        return 1

    return 0


def detect_location(text, default="Not specified"):
    """Find a known city or country in the text, else fall back to Online."""
    lowered = text.lower()

    for place in KNOWN_LOCATIONS:
        # Word-boundary match so "Goa" does not fire inside "goal".
        if re.search(r"\b" + re.escape(place.lower()) + r"\b", lowered):
            return place

    for hint in ONLINE_HINTS:
        if hint in lowered:
            return "Online"

    return default


def detect_mode(text, location):
    """Online or Offline - drives the Online/Offline filter."""
    lowered = text.lower()
    if location == "Online":
        return "Online"
    for hint in ONLINE_HINTS:
        if hint in lowered:
            return "Online"
    return "Offline"


def clean_title(text):
    """Collapse whitespace and strip leading/trailing junk from a title."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.strip("-–—|·•,;: \t\n")
    return cleaned
