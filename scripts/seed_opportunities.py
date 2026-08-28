"""
Seed the curated priority opportunities into the events table.

Idempotent: rows are keyed by the same fingerprint the scraper uses, so
re-running updates the existing record in place instead of creating a second
copy. Safe to run after every crawl.

    python -m scripts.seed_opportunities --dry-run
    python -m scripts.seed_opportunities
"""

import argparse
import sys
from datetime import datetime

from config.course_filter import is_course
from config.priority import assign_location, geo_score, match_tags
from config.priority_opportunities import PRIORITY_OPPORTUNITIES, VERIFIED_ON
from database.db import get_connection, init_db
from scraper import classifier
from scraper.extractor import make_fingerprint

SOURCE_NAME = "Curated priority list"

# Columns the seeder writes. `title` and `fingerprint` are handled separately.
FIELDS = [
    "category", "subcategory", "description", "organizer", "location",
    "country", "region", "mode", "date", "date_iso", "start_date", "end_date",
    "deadline", "source_url", "application_url", "registration_url", "website",
    "eligibility", "cost", "prize_or_funding", "tags", "status", "focus",
    "source", "is_verified", "city", "priority_tags", "geo_score",
]


def _human_date(start, end):
    """"28 Oct 2026" or "28 Oct - 31 Oct 2026"; empty when undated."""
    if not start:
        return ""
    fmt = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
    if end and end != start:
        return f"{fmt(start)} - {fmt(end)}"
    return fmt(start)


def _status(start, end):
    """Past events are Closed; undated ones stay Open so they remain visible."""
    if not start:
        return "Open"
    last = end or start
    return "Closed" if last < datetime.utcnow().date().isoformat() else "Open"


def build_row(entry):
    """Turn one curated dict into the full column set."""
    title = entry["title"]
    start = entry.get("start_date", "")
    end = entry.get("end_date", "")

    row = {key: entry.get(key, "") for key in FIELDS}
    row["date_iso"] = start
    row["date"] = _human_date(start, end)
    row["status"] = _status(start, end)
    row["source"] = SOURCE_NAME
    row["is_verified"] = 1
    # These two are what the existing UI reads for its links, so mirror the
    # curated values into them rather than leaving the buttons dead.
    row["registration_url"] = entry.get("application_url") or entry.get("source_url", "")
    row["website"] = entry.get("source_url", "")
    row["focus"] = classifier.focus_score(
        title, entry.get("category", ""), entry.get("description", "")
    )

    # Same priority computation the scraper runs, so curated and scraped rows
    # sort against each other on one scale. Location comes from the location
    # fields only; the collection tags come from the record's own organiser,
    # title, description and tags, so none is attached without evidence.
    country, region, city, tier = assign_location(
        region=entry.get("region", ""), country=entry.get("country", ""),
        location=entry.get("location", ""), mode=entry.get("mode", ""),
    )
    row["country"], row["region"], row["city"] = country, region, city
    row["priority_tags"] = match_tags(
        title, entry.get("organizer", ""), entry.get("tags", ""),
        entry.get("description", ""), entry.get("category", ""),
    )
    row["geo_score"] = geo_score(tier, city, row["priority_tags"])
    return title, row


def seed(dry_run=False, verbose=True):
    """
    Write every curated entry, returning (added, updated).

    Exposed as a function because main.py calls it on start-up: a fresh
    deployment - or a new persistent disk - should never come up as an empty
    dashboard, and the fingerprinting makes repeat runs harmless.
    """
    def say(message):
        if verbose:
            print(message)

    init_db()
    conn = get_connection()
    added = updated = 0
    try:
        for entry in PRIORITY_OPPORTUNITIES:
            title, row = build_row(entry)

            # A curated entry must never trip the course filter. If one does it
            # is a bug in either the title or the filter, and silently dropping
            # it would hide that.
            if is_course(title):
                say(f"  !! REFUSED as course: {title}")
                continue

            # Deliberately fingerprinted on the title alone, with no date.
            # The scraper includes the date because a re-run of the same
            # conference next year is a genuinely new event; a curated entry
            # is the opposite - it is one tracked opportunity whose date is
            # expected to be filled in later. Including the date would make
            # "BYOG, date TBA" and "BYOG, 9 Oct" two rows instead of one.
            fingerprint = make_fingerprint(SOURCE_NAME, title, "")
            existing = conn.execute(
                "SELECT id FROM events WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()

            verdict = "update" if existing else "add"
            say(f"  [{verdict:6}] {row['category']:16} {title}")
            if dry_run:
                continue

            if existing:
                sets = ", ".join(f"{f} = ?" for f in FIELDS)
                conn.execute(
                    f"UPDATE events SET {sets}, last_verified_at = ? WHERE id = ?",
                    [row[f] for f in FIELDS] + [VERIFIED_ON, existing["id"]],
                )
                updated += 1
            else:
                cols = ["title", "fingerprint", "created_at", "is_new",
                        "last_verified_at"] + FIELDS
                conn.execute(
                    f"INSERT INTO events ({', '.join(cols)}) "
                    f"VALUES ({', '.join('?' * len(cols))})",
                    [title, fingerprint, datetime.utcnow().isoformat(), 1,
                     VERIFIED_ON] + [row[f] for f in FIELDS],
                )
                added += 1

        if dry_run:
            say("\nDry run - nothing written.")
            return added, updated

        conn.commit()
        say(f"\n{added} added, {updated} updated.")
        return added, updated
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be written without writing")
    args = parser.parse_args()
    seed(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
