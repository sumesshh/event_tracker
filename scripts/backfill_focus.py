"""
One-off maintenance script: score every event already in the database.

The `focus` column (games / AR-VR / apps ranking) was added after the first
crawls had already run, so existing rows carry the default 0. This re-runs the
classifier over them - it also re-files categories, because the category rules
changed at the same time.

    python -m scripts.backfill_focus
"""

from config.categories import CATEGORIES
from database import db
from scraper import classifier
from utils.logger import get_logger

log = get_logger("backfill")


def purge_noise():
    """
    Delete stored rows that the current noise rules would now reject.

    The rules were tightened after these rows were crawled, so marketing copy
    like "Get the Azure mobile app" is still sitting in the table. They cannot
    come back: the crawler re-checks every candidate against the same rules.
    """
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT id, title FROM events").fetchall()
        doomed = [
            (row["id"],)
            for row in rows
            if classifier.is_noise(row["title"]) or classifier.is_past_report(row["title"])
        ]
        conn.executemany("DELETE FROM events WHERE id = ?", doomed)
        conn.commit()
        log.info("Removed %d non-event rows", len(doomed))
        return len(doomed)
    finally:
        conn.close()


def backfill():
    """Recompute category + focus for every stored event."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, category, location, source FROM events"
        ).fetchall()

        recategorised = 0
        updates = []

        for row in rows:
            title = row["title"]
            # The card text is long gone, so score on what we kept. The title
            # is the strongest signal anyway.
            context = f"{row['source']} {row['location']}"

            category = classifier.detect_category(title, default="")
            if not category:
                # Keep whatever the original crawl decided rather than guessing
                # from a source name.
                category = row["category"]
            elif category != row["category"]:
                recategorised += 1

            focus = classifier.focus_score(title, category, context)
            updates.append((category, focus, row["id"]))

        conn.executemany(
            "UPDATE events SET category = ?, focus = ? WHERE id = ?", updates
        )
        conn.commit()

        focused = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE focus > 0"
        ).fetchone()["c"]

        log.info(
            "Backfilled %d events: %d recategorised, %d now in focus",
            len(updates), recategorised, focused,
        )
        return len(updates), recategorised, focused
    finally:
        conn.close()


if __name__ == "__main__":
    db.init_db()
    removed = purge_noise()
    total, recategorised, focused = backfill()
    print(f"Removed {removed} non-event rows.")
    print(f"Scored {total} events.")
    print(f"  recategorised: {recategorised}")
    print(f"  in focus (game / AR-VR / apps): {focused}")
    print(f"  categories in use: {', '.join(CATEGORIES)}")
