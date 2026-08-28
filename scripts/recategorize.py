"""
Re-run the categoriser over every stored event.

Rows written before the opportunity categories existed (Grant, Funding,
Hackathon, Competition, Program, ...) still carry the old labels - a grant
filed under "Workshop", a game jam under "Gaming". This replays
classifier.detect_category over the stored titles so the filter bar and the
per-category counts reflect the current rules.

Run it after scripts.purge_courses, so courses are gone before recounting.

    python -m scripts.recategorize --dry-run
    python -m scripts.recategorize
"""

import argparse
import sys
from collections import Counter

from database.db import get_connection
from scraper import classifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report the changes without writing them")
    args = parser.parse_args()

    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, title, category FROM events").fetchall()
        changes = []
        for row in rows:
            # Title only - the same signal the extractor trusts most. The
            # surrounding card text is not stored, so there is nothing else to
            # fall back to here.
            new = classifier.detect_category(row["title"], default="Technology Event")
            if new != row["category"]:
                changes.append((new, row["id"], row["category"], row["title"]))

        moves = Counter((old, new) for new, _, old, _ in changes)
        for (old, new), count in moves.most_common():
            print(f"  {old:12} -> {new:12}  {count}")
        print(f"\n{len(changes)} of {len(rows)} events change category.")

        if args.dry_run:
            print("Dry run - nothing written.")
            return 0

        conn.executemany(
            "UPDATE events SET category = ? WHERE id = ?",
            [(new, rid) for new, rid, _, _ in changes],
        )
        conn.commit()

        print("\nCategory counts now:")
        for cat, count in conn.execute(
            "SELECT category, COUNT(*) c FROM events GROUP BY category ORDER BY c DESC"
        ):
            print(f"  {cat:12} {count}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
