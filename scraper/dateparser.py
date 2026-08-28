"""
Date extraction, written with the standard library only (no paid or heavy
third-party date libraries).

Event pages write dates in wildly different shapes:

    "12 March 2026"        "March 12, 2026"     "2026-03-12"
    "12/03/2026"           "Mar 12 - 14, 2026"  "12 - 14 March 2026"

`extract_date` finds the first one it recognises in a blob of text and returns
both the original human-readable string and an ISO date used for sorting.
"""

import re
from datetime import datetime

# Month name -> month number, covering full names and three letter forms.
MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_ALT = "|".join(sorted(MONTHS.keys(), key=len, reverse=True))

# Each pattern is (compiled regex, handler name). Order matters: the most
# specific formats are tried first.
PATTERNS = [
    # 2026-03-12  /  2026/03/12
    (re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b"), "ymd"),

    # 12 March 2026  /  12th Mar, 2026  /  12 - 14 March 2026
    (re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:[-–—]\s*\d{1,2}(?:st|nd|rd|th)?\s*)?"
        r"(" + _MONTH_ALT + r")\.?,?\s*(20\d{2})\b", re.I), "dmy"),

    # March 12, 2026  /  Mar 12 - 14, 2026
    (re.compile(
        r"\b(" + _MONTH_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
        r"(?:\s*[-–—]\s*\d{1,2}(?:st|nd|rd|th)?)?,?\s*(20\d{2})\b", re.I), "mdy"),

    # 12/03/2026 - read as day/month/year, the Indian convention
    (re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b"), "dmy_numeric"),

    # 05/27/26 - two-digit year, seen on US-style "Apply By" dates
    (re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2})\b"), "mdy_short"),

    # "March 2026" with no day - assume the 1st
    (re.compile(r"\b(" + _MONTH_ALT + r")\.?\s+(20\d{2})\b", re.I), "my"),

    # "September 06" with no year at all - common on "upcoming" widgets that
    # only show near-term dates. Tried last since it is the most ambiguous.
    (re.compile(
        r"\b(" + _MONTH_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.I), "md_noyear"),
]


def _build(year, month, day):
    """Return an ISO date string, or None when the numbers are not a real date."""
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except (ValueError, TypeError):
        return None


def parse_date_string(text):
    """
    Find the first recognisable date in `text`.

    Returns (raw_text, iso_date) where raw_text is exactly what appeared on the
    page, or (None, None) when nothing looks like a date.
    """
    if not text:
        return None, None

    for pattern, kind in PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        groups = match.groups()
        iso = None

        if kind == "ymd":
            iso = _build(groups[0], groups[1], groups[2])
        elif kind == "dmy":
            iso = _build(groups[2], MONTHS[groups[1].lower().rstrip(".")], groups[0])
        elif kind == "mdy":
            iso = _build(groups[2], MONTHS[groups[0].lower().rstrip(".")], groups[1])
        elif kind == "dmy_numeric":
            iso = _build(groups[2], groups[1], groups[0])
        elif kind == "mdy_short":
            year = 2000 + int(groups[2])
            # Month is always the leading number here (US "Apply By" style);
            # try it as month/day and fall back to day/month if that fails.
            iso = _build(year, groups[0], groups[1]) or _build(year, groups[1], groups[0])
        elif kind == "my":
            iso = _build(groups[1], MONTHS[groups[0].lower().rstrip(".")], 1)
        elif kind == "md_noyear":
            # No year on the page: assume this year, unless that date is
            # already well in the past, in which case the listing means
            # next year's occurrence.
            today = datetime.today().date()
            month = MONTHS[groups[0].lower().rstrip(".")]
            day = int(groups[1])
            year = today.year
            candidate = _build(year, month, day)
            if candidate and datetime.fromisoformat(candidate).date() < today.replace(day=1):
                candidate = _build(year + 1, month, day)
            iso = candidate

        if iso:
            return match.group(0).strip(), iso

    return None, None


def extract_date(element, fallback_text=""):
    """
    Pull a date out of one HTML element.

    Structured markup is checked first (<time datetime="...">, schema.org
    attributes) because it is unambiguous; only then do we fall back to
    scanning the visible text.
    """
    if element is not None:
        # <time datetime="2026-03-12T09:00:00+05:30">
        time_tag = element.find("time")
        if time_tag:
            iso_attr = time_tag.get("datetime") or time_tag.get("content")
            if iso_attr:
                raw, iso = parse_date_string(iso_attr[:10])
                if iso:
                    return time_tag.get_text(strip=True) or raw, iso
            raw, iso = parse_date_string(time_tag.get_text(" ", strip=True))
            if iso:
                return raw, iso

        # schema.org microdata: <meta itemprop="startDate" content="...">
        meta = element.find(attrs={"itemprop": "startDate"})
        if meta:
            raw, iso = parse_date_string(meta.get("content", "") or meta.get_text(" ", strip=True))
            if iso:
                return raw, iso

        # Any element whose class name mentions a date.
        dated = element.find(
            attrs={"class": re.compile(r"date|when|schedule|timing", re.I)}
        )
        if dated:
            raw, iso = parse_date_string(dated.get_text(" ", strip=True))
            if iso:
                return raw, iso

        raw, iso = parse_date_string(element.get_text(" ", strip=True))
        if iso:
            return raw, iso

    return parse_date_string(fallback_text)
