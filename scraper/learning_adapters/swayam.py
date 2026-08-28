"""
SWAYAM (Study Webs of Active Learning for Young Aspiring Minds) adapter.

SWAYAM is the Government of India's official MOOC platform
(https://swayam.gov.in - Ministry of Education / AICTE). Its course explorer
page (https://swayam.gov.in/explorer) server-renders a JSON blob of the
currently listed courses inside a `<script>` tag - no JavaScript rendering or
private API key needed, just a plain GET and a JSON parse. This is real,
individual per-course data (title, instructor, institute, start/end/
enrolment dates, credits, weeks, discipline) straight from the source that
runs the platform, which is exactly the "discover individual courses, not one
platform entry" shape rule #5 of the brief asks for.

What we can and cannot verify from this page:
  * Course identity, dates, instructor, institute, discipline - all real,
    read directly off the explorer feed.
  * Enrolment is documented SWAYAM-wide policy as free
    (https://swayam.gov.in - "About" - no cost for course access).
  * Certificate eligibility depends on registering separately for a paid,
    proctored exam per course; the explorer feed does not expose a
    per-course flag for whether that exam is currently open, so
    certificate_available is left "unknown" rather than assumed true for
    every course.
"""

import json
from datetime import datetime

from scraper.fetcher import fetch_url
from utils.logger import get_logger

log = get_logger("learning.swayam")

EXPLORER_URL = "https://swayam.gov.in/explorer"

# SWAYAM's own discipline codes -> our normalised Learning categories.
# Anything not listed falls back to "Skill Development" / "EdTech".
CATEGORY_MAP = {
    "COMP_SCI_ENGG": ["Programming", "Software Development"],
    "Computer_Science": ["Programming", "Software Development"],
    "Computer_Applications": ["Programming", "Software Development"],
    "INF_SYSTEMS": ["Data Science", "Cloud"],
    "ELEC_ENGG": ["STEM"],
    "BIO_TECH": ["STEM", "Research"],
    "Management": ["Business"],
    "MGMT_COMM": ["Business", "Career Development"],
    "HRM_ORG_BEHAVIOUR": ["Business", "Leadership"],
    "Marketing": ["Digital Marketing", "Business"],
    "Commerce": ["Finance", "Business"],
    "Finance": ["Finance"],
    "Language": ["Language"],
    "TEACHER_EDUCATION": ["Career Development"],
    "Humanities_and_Social_Sciences": ["Skill Development"],
    "Mathematics": ["STEM"],
    "AGRI_COURSES": ["STEM"],
    "TEXTILE_COURSES": ["STEM"],
    "Multidisciplinary": ["Skill Development"],
}


def _extract_course_edges(html):
    """
    Pull the `{"edges": [{"node": {...}}, ...]}` course-list JSON blob out of
    the server-rendered explorer page. The page embeds it as a plain JS
    object literal (single-quoted keys around it, double-quoted JSON inside),
    so a brace-matching scan starting at the first `{"edges":` is more
    reliable than a regex against the surrounding markup.
    """
    marker = '{"edges": [{"node"'
    start = html.find(marker)
    if start == -1:
        return []

    depth = 0
    in_str = False
    esc = False
    i = start
    while i < len(html):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
        i += 1

    try:
        data = json.loads(html[start:i])
    except json.JSONDecodeError:
        log.warning("SWAYAM explorer JSON did not parse cleanly")
        return []

    return data.get("edges", [])


def _to_date(value):
    """SWAYAM gives ISO datetimes ("2026-08-23T18:30:00.000000Z") -> YYYY-MM-DD."""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _map_categories(raw_categories):
    mapped = set()
    for entry in raw_categories or []:
        name = entry.get("name", "")
        mapped.update(CATEGORY_MAP.get(name, []))
    mapped.add("EdTech")
    if not mapped - {"EdTech"}:
        mapped.add("Skill Development")
    return sorted(mapped)


def fetch():
    """DISCOVER + EXTRACT: one page of currently listed SWAYAM courses."""
    html = fetch_url(EXPLORER_URL)
    if not html:
        log.warning("Could not fetch SWAYAM explorer page")
        return []

    edges = _extract_course_edges(html)
    if not edges:
        log.warning("No courses found in SWAYAM explorer feed - page layout may have changed")
        return []

    programs = []
    for edge in edges:
        node = edge.get("node") or {}
        title = (node.get("title") or "").strip()
        url = node.get("url") or ""
        if not title or not url:
            continue

        program_aligned = node.get("programAlignedTo") or ""

        programs.append({
            "title": title,
            "provider": "SWAYAM",
            # explorerSummary is frequently null on the listing feed; left
            # blank (not fabricated) when the platform does not supply one.
            "description": node.get("explorerSummary") or "",
            "category": _map_categories(node.get("category")),
            "subcategory": "Online Courses",
            "program_type": "Course",
            "country": "India",
            "city": "",
            "location_type": "Online",
            # SWAYAM content is publicly viewable worldwide; the government
            # platform itself is India-run, so eligibility for the official
            # certification exam is India-specific while the course content
            # is open globally.
            "eligible_countries": ["India", "Global"],
            "cost_type": "FREE",
            "price": 0,
            "currency": "INR",
            "funding_type": "NONE",
            "funding_amount": "",
            # Not exposed per-course on the explorer feed - see module
            # docstring. Left unknown rather than assumed.
            "certificate_available": "unknown",
            "eligibility": {
                "programAlignedTo": program_aligned,
                "instructor": node.get("explorerInstructorName") or "",
                "institute": node.get("instructorInstitute") or "",
                "courseLanguage": node.get("courseLanguage") or "",
                "credits": node.get("credits"),
                "weeks": node.get("weeks"),
            },
            "start_date": _to_date(node.get("startDate")),
            "end_date": _to_date(node.get("endDate")),
            "application_deadline": _to_date(node.get("enrollmentEndDate")),
            "official_url": url,
            "application_url": url,
            "source_type": "GOVERNMENT",
            "source_name": "SWAYAM",
        })

    log.info("SWAYAM: extracted %d courses from the explorer feed", len(programs))
    return programs


ADAPTER = {
    "name": "SWAYAM",
    "source_type": "GOVERNMENT",
    "fetch": fetch,
}
