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
    CAREER_PATHS_VOCAB,
    CATEGORY_KEYWORDS,
    CERTIFICATE_KEYWORDS,
    FOCUS_CATEGORIES,
    FOCUS_KEYWORDS,
    FORMAT_KEYWORDS,
    FUNDING_TYPE_KEYWORDS,
    LEARNING_CATEGORY_KEYWORDS,
    LEARNING_SIGNAL_KEYWORDS,
    LEVEL_KEYWORDS,
    NOISE_KEYWORDS,
    PAST_REPORT_KEYWORDS,
    PROGRAM_TYPE_KEYWORDS,
    RELEVANCE_KEYWORDS,
    SKILLS_VOCAB,
    STRONG_EVENT_KEYWORDS,
)

# Cities that show up often in the sources we crawl. Detecting one gives the
# event a real location instead of "Not specified".
KNOWN_LOCATIONS = [
    # Kerala
    "Kochi", "Cochin", "Ernakulam", "Trivandrum", "Thiruvananthapuram",
    "Kozhikode", "Calicut", "Thrissur", "Kollam", "Kannur", "Kerala",
    # Rest of India
    "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Mumbai", "Pune",
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


def is_noise(title):
    """True for navigation links, footers and other non-event text."""
    if not title:
        return True

    cleaned = title.strip()

    # Too short to be a real event name, or so long it is a paragraph.
    if len(cleaned) < 12 or len(cleaned) > 180:
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

    # Mostly punctuation / numbers rather than words.
    letters = sum(ch.isalpha() for ch in cleaned)
    if letters < len(cleaned) * 0.5:
        return True

    # Needs at least two words to be a title.
    if len(cleaned.split()) < 2:
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


def detect_category(text, default="Technology"):
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


# ---------------------------------------------------------------------------
# EdTech & Learning Programs
# ---------------------------------------------------------------------------
# Pre-compiled once at import time, same reasoning as the event patterns above.
_LEARNING_SIGNAL_PATTERN = _compile_keywords(LEARNING_SIGNAL_KEYWORDS)
_LEARNING_CATEGORY_PATTERNS = [
    (name, _compile_keywords(keywords))
    for name, keywords in LEARNING_CATEGORY_KEYWORDS.items()
]
_PROGRAM_TYPE_PATTERNS = [
    (name, _compile_keywords(keywords)) for name, keywords in PROGRAM_TYPE_KEYWORDS.items()
]
_LEVEL_PATTERNS = [
    (name, _compile_keywords(keywords)) for name, keywords in LEVEL_KEYWORDS.items()
]
_FORMAT_PATTERNS = [
    (name, _compile_keywords(keywords)) for name, keywords in FORMAT_KEYWORDS.items()
]
_FUNDING_TYPE_PATTERNS = [
    (name, _compile_keywords(keywords)) for name, keywords in FUNDING_TYPE_KEYWORDS.items()
]
_CERTIFICATE_PATTERNS = [
    (name, _compile_keywords(keywords)) for name, keywords in CERTIFICATE_KEYWORDS.items()
]
_SKILLS_PATTERN = _compile_keywords(SKILLS_VOCAB)
_CAREER_PATHS_PATTERN = _compile_keywords(CAREER_PATHS_VOCAB)


def is_learning_opportunity(text):
    """
    True when the text describes an education / training / scholarship style
    opportunity rather than a plain event.

    Also true for anything that already lands in a learning category (a
    "Unity Bootcamp" mentions Game Development without necessarily using one
    of the generic LEARNING_SIGNAL_KEYWORDS).
    """
    if _LEARNING_SIGNAL_PATTERN.search(text):
        return True
    return any(pattern.search(text) for _, pattern in _LEARNING_CATEGORY_PATTERNS)


def detect_learning_categories(text):
    """All matching Education & Learning tags, e.g. ["EdTech", "AI & Machine Learning"]."""
    return [name for name, pattern in _LEARNING_CATEGORY_PATTERNS if pattern.search(text)]


def detect_program_type(text, default="Course"):
    """First matching program type; PROGRAM_TYPE_KEYWORDS is ordered specific -> general."""
    for name, pattern in _PROGRAM_TYPE_PATTERNS:
        if pattern.search(text):
            return name
    return default


def detect_level(text, default="Beginner"):
    for name, pattern in _LEVEL_PATTERNS:
        if pattern.search(text):
            return name
    return default


def detect_format(text, mode):
    """Online / Offline / Hybrid. Falls back to the event mode already detected."""
    for name, pattern in _FORMAT_PATTERNS:
        if pattern.search(text):
            return name
    return mode if mode in ("Online", "Offline") else "Offline"


def detect_funding_type(text, default="Unknown"):
    """
    Cost / funding classification.

    Order matters: "fully funded" must win over a stray "free" match, and a
    course that only mentions a fee is Paid even if an intro module is free -
    the "free intro" phrasing is deliberately excluded from the Free keywords.
    """
    lowered = f" {text.lower()} "
    for name, pattern in _FUNDING_TYPE_PATTERNS:
        if pattern.search(lowered):
            return name
    return default


def detect_certificate(text, default="Unknown"):
    for name, pattern in _CERTIFICATE_PATTERNS:
        if pattern.search(text):
            return name
    return default


def extract_skills(text):
    """Every known skill mentioned in the text, in vocabulary order."""
    lowered = text.lower()
    found = []
    for skill in SKILLS_VOCAB:
        if re.search(r"\b" + re.escape(skill.lower()) + r"\b", lowered):
            found.append(skill)
    return found


def extract_career_paths(text):
    """Every known career path mentioned in the text, in vocabulary order."""
    lowered = text.lower()
    return [path for path in CAREER_PATHS_VOCAB if path.lower() in lowered]


def clean_title(text):
    """Collapse whitespace and strip leading/trailing junk from a title."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.strip("-–—|·•,;: \t\n")
    return cleaned
