"""
Bring every stored row onto the current data rules.

Three passes, in this order:

  1. PURGE   - delete rows the current filters would never have accepted:
               course listings (config.course_filter), calendar cells and
               section labels scraped as titles, past-tense news reports
               about events that already happened, and undated fragments that
               name no opportunity type at all (scraper.classifier).

  2. LOCATE  - recompute country / region / city from the location fields the
               source published. Rows stored before config/regions.py existed
               carry "India" or "Global" in the state column, which made the
               State filter offer things that are not states.

  3. SCORE   - recompute the priority collections and geo_score every listing
               is sorted on (config/priority.py).

Passes 2 and 3 only rewrite derived columns, so the script is idempotent and
safe to re-run after any keyword change.

    python -m scripts.clean_data --dry-run
    python -m scripts.clean_data
"""

import argparse
import sys

from config.course_filter import course_reason, is_course
from config.priority import assign_location, geo_score, match_tags
from database.db import get_connection, init_db, refresh_statuses
from scraper import classifier


def _junk_reason(row):
    """Why this row does not belong in the table, or None if it does."""
    title = row["title"] or ""
    if is_course(title):
        return f"course ({course_reason(title)})"
    if classifier.is_noise(title):
        return "noise"
    if classifier.is_past_report(title):
        return "past report"
    # No date and no opportunity word: a page fragment ("What muLearn offers",
    # "Innovation Zone", "MORE ON INC42") rather than something anyone can
    # apply to or attend. A real undated opportunity names its type, which is
    # exactly what looks_like_opportunity tests for.
    if not (row["date_iso"] or "") and not classifier.looks_like_opportunity(title):
        return "no date, no opportunity"
    return None


def purge(conn, dry_run):
    """Pass 1 - drop everything the current rules reject."""
    doomed = []
    for row in conn.execute(
            "SELECT id, title, category, source, date_iso FROM events"
    ):
        reason = _junk_reason(row)
        if reason:
            doomed.append((row["id"], reason, row["title"], row["source"]))

    for _, reason, title, source in doomed[:40]:
        print(f"  [{reason:22}] {title[:64]} ({source})")
    if len(doomed) > 40:
        print(f"  ... and {len(doomed) - 40} more")

    if not dry_run and doomed:
        conn.executemany(
            "DELETE FROM events WHERE id = ?", [(i,) for i, *_ in doomed]
        )
    return len(doomed)


def relocate_and_score(conn, dry_run):
    """Passes 2 and 3 - recompute the derived location, tag and score columns."""
    changed = 0
    updates = []

    rows = conn.execute(
        "SELECT id, title, category, organizer, source, tags, description, "
        "location, country, region, city, mode, priority_tags, geo_score "
        "FROM events"
    ).fetchall()

    for row in rows:
        country, region, city, tier = assign_location(
            region=row["region"], country=row["country"],
            location=row["location"], mode=row["mode"],
        )
        tags = match_tags(
            row["title"], row["organizer"], row["source"], row["tags"],
            row["description"], row["category"],
        )
        score = geo_score(tier, city, tags)

        if (country, region, city, tags, score) != (
            row["country"], row["region"], row["city"] or "",
            row["priority_tags"] or "", row["geo_score"],
        ):
            changed += 1
            updates.append((country, region, city, tags, score, row["id"]))

    if not dry_run and updates:
        conn.executemany(
            "UPDATE events SET country = ?, region = ?, city = ?, "
            "priority_tags = ?, geo_score = ? WHERE id = ?",
            updates,
        )
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args()

    init_db()
    conn = get_connection()
    try:
        before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        print("Pass 1 - purging courses, noise and past reports")
        removed = purge(conn, args.dry_run)

        print("\nPass 2/3 - locations, priority tags and scores")
        rescored = relocate_and_score(conn, args.dry_run)

        if args.dry_run:
            print(f"\nDry run. {before} rows: would delete {removed}, "
                  f"would rewrite {rescored}.")
            return 0

        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        print(f"\nDeleted {removed}, rewrote {rescored}. {before} -> {after} rows.")
    finally:
        conn.close()

    refresh_statuses()
    return 0


if __name__ == "__main__":
    sys.exit(main())
