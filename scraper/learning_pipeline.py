"""
The Learning Programs ingestion pipeline:

    SOURCE -> DISCOVER -> EXTRACT -> NORMALIZE -> VERIFY -> STORE

Each adapter in scraper/learning_adapters/ is responsible for SOURCE,
DISCOVER and EXTRACT - it fetches one real official page (or a small set of
them) and returns a list of raw program dicts already close to the final
shape. This module does the shared, source-independent part: normalising
values into the fixed vocabularies, verifying the required fields are
actually present, computing the stable id used for de-duplication, and
writing to database/learning_db.py.

Run standalone for testing:

    python -m scraper.learning_pipeline
"""

import hashlib
import re
import threading
from datetime import datetime, timedelta

from config.categories import SKILLS_VOCAB
from database import learning_db
from utils.logger import get_logger

log = get_logger("learning_pipeline")

_lock = threading.Lock()

CLOSING_SOON_DAYS = 14

VALID_COST_TYPES = {"FREE", "PAID", "SCHOLARSHIP", "PARTIALLY_FUNDED", "FULLY_FUNDED", "UNKNOWN"}
VALID_FUNDING_TYPES = {"NONE", "SCHOLARSHIP", "GRANT", "STIPEND", "FULLY_FUNDED", "PARTIALLY_FUNDED", "UNKNOWN"}
VALID_LOCATION_TYPES = {"Online", "Offline", "Hybrid", "Unknown"}
VALID_SOURCE_TYPES = {"GOVERNMENT", "UNIVERSITY", "INSTITUTION", "COMPANY", "PROVIDER", "SECONDARY"}


def make_program_id(provider, title, url):
    """
    Stable de-duplication key: normalised title + provider + URL (rule #13).
    Re-running an adapter on the same course therefore updates the existing
    row (upsert) instead of inserting a duplicate.
    """
    normalised_title = re.sub(r"[^a-z0-9]+", "", title.lower())
    raw = f"{provider.lower()}|{normalised_title}|{url.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_skills(text):
    lowered = text.lower()
    return [s for s in SKILLS_VOCAB if re.search(r"\b" + re.escape(s.lower()) + r"\b", lowered)]


def normalize_and_verify(raw):
    """
    Turn one adapter's raw dict into a fully-shaped, stored-ready program.

    Required fields (title, provider, official_url) missing -> the record is
    rejected outright (rule #12: "verify title/provider/official URL"). Every
    other field that the adapter did not confidently determine is left as the
    documented "unknown" value rather than guessed.
    """
    title = (raw.get("title") or "").strip()
    provider = (raw.get("provider") or "").strip()
    official_url = (raw.get("official_url") or "").strip()

    if not title or not provider or not official_url.startswith(("http://", "https://")):
        log.warning("Rejected program - missing title/provider/official_url: %r", raw)
        return None

    description = (raw.get("description") or "").strip()
    haystack = f"{title} {description}"

    cost_type = raw.get("cost_type", "UNKNOWN")
    if cost_type not in VALID_COST_TYPES:
        cost_type = "UNKNOWN"

    funding_type = raw.get("funding_type", "UNKNOWN")
    if funding_type not in VALID_FUNDING_TYPES:
        funding_type = "UNKNOWN"

    location_type = raw.get("location_type", "Unknown")
    if location_type not in VALID_LOCATION_TYPES:
        location_type = "Unknown"

    source_type = raw.get("source_type", "SECONDARY")
    if source_type not in VALID_SOURCE_TYPES:
        source_type = "SECONDARY"

    cert = raw.get("certificate_available", "unknown")
    if cert not in (True, False):
        cert = "unknown"

    skills = raw.get("skills")
    if not skills:
        skills = _extract_skills(haystack)

    program = {
        "id": make_program_id(provider, title, official_url),
        "title": title,
        "provider": provider,
        "description": description,
        "category": raw.get("category") or [],
        "subcategory": raw.get("subcategory", ""),
        "skills": skills,
        "program_type": raw.get("program_type", "Course"),
        "country": raw.get("country") or "Unknown",
        "city": raw.get("city", ""),
        "location_type": location_type,
        "eligible_countries": raw.get("eligible_countries") or [],
        "cost_type": cost_type,
        "price": raw.get("price"),
        "currency": raw.get("currency", ""),
        "funding_type": funding_type,
        "funding_amount": raw.get("funding_amount", ""),
        "certificate_available": cert,
        "eligibility": raw.get("eligibility") or {},
        "start_date": raw.get("start_date", ""),
        "end_date": raw.get("end_date", ""),
        "application_deadline": raw.get("application_deadline", ""),
        "official_url": official_url,
        "application_url": raw.get("application_url") or official_url,
        "source_type": source_type,
        "source_name": raw.get("source_name", provider),
        # Only a real official/government/university source is marked
        # verified; anything discovered via a secondary page is stored but
        # flagged unverified until cross-checked against the official page
        # (rule #16).
        "verified": source_type != "SECONDARY",
        "last_verified_at": datetime.utcnow().isoformat(timespec="seconds"),
    }

    today = datetime.utcnow().date()
    soon = today + timedelta(days=CLOSING_SOON_DAYS)
    program["status"] = learning_db._compute_status(
        program["start_date"], program["application_deadline"], today, soon
    )

    return program


def run_source(adapter):
    """
    Run one adapter end-to-end: DISCOVER + EXTRACT (adapter) -> NORMALIZE +
    VERIFY (this module) -> STORE (database.learning_db).

    Returns a summary dict; never raises, so one broken source cannot take
    down the whole ingestion run.
    """
    name = adapter["name"]
    log.info("Learning source: %s", name)
    try:
        raw_programs = adapter["fetch"]()
    except Exception as exc:                      # noqa: BLE001
        log.exception("Adapter %s failed: %s", name, exc)
        return {"source": name, "ok": False, "discovered": 0, "stored": 0, "new": 0}

    stored_ids = []
    new_count = 0
    for raw in raw_programs:
        raw.setdefault("source_name", name)
        program = normalize_and_verify(raw)
        if not program:
            continue
        is_new = learning_db.upsert_program(program)
        stored_ids.append(program["id"])
        if is_new:
            new_count += 1

    removed = learning_db.delete_stale(name, set(stored_ids))

    log.info(
        "  %s: %d discovered, %d stored, %d new, %d removed (no longer listed)",
        name, len(raw_programs), len(stored_ids), new_count, removed,
    )
    return {
        "source": name, "ok": True, "discovered": len(raw_programs),
        "stored": len(stored_ids), "new": new_count, "removed": removed,
    }


def run_ingestion():
    """Run every registered adapter once, then recompute every status."""
    if not _lock.acquire(blocking=False):
        log.info("Learning ingestion already running - skipping this trigger")
        return {"skipped": True}

    from scraper.learning_adapters import LEARNING_SOURCES

    started_at = datetime.utcnow().isoformat(timespec="seconds")
    log.info("=" * 60)
    log.info("Learning Programs ingestion started at %s UTC", started_at)

    try:
        results = [run_source(adapter) for adapter in LEARNING_SOURCES]
        learning_db.refresh_all_statuses(CLOSING_SOON_DAYS)

        totals = {
            "sources_ok": sum(1 for r in results if r["ok"]),
            "sources_failed": sum(1 for r in results if not r["ok"]),
            "discovered": sum(r.get("discovered", 0) for r in results),
            "new": sum(r.get("new", 0) for r in results),
        }
        log.info(
            "Learning ingestion finished: %d sources ok, %d failed, %d discovered, %d new",
            totals["sources_ok"], totals["sources_failed"], totals["discovered"], totals["new"],
        )
        log.info("=" * 60)
        return {"skipped": False, "results": results, **totals}
    finally:
        _lock.release()


if __name__ == "__main__":
    learning_db.init_db()
    summary = run_ingestion()
    print(summary)
