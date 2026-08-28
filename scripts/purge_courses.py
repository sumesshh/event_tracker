"""
Delete course listings stored before config.course_filter existed.

Ingestion now rejects courses at the extractor and again at insert, so this is
a one-off cleanup for historical rows - but it is safe to re-run at any time
and is worth running after changing the keyword lists.

    python -m scripts.purge_courses --dry-run   # list what would go
    python -m scripts.purge_courses             # delete it
"""

import argparse
import sys

from config.course_filter import course_reason, is_course
from database.db import get_connection


def find_courses(conn):
    """Every stored row the course filter now rejects."""
    rows = conn.execute("SELECT id, title, category FROM events").fetchall()
    return [r for r in rows if is_course(r["title"])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="list the matching rows without deleting them",
    )
    args = parser.parse_args()

    conn = get_connection()
    try:
        doomed = find_courses(conn)
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        for row in doomed:
            print(f"  [{course_reason(row['title'])}] {row['category']} | {row['title']}")

        print(f"\n{len(doomed)} course listings of {total} events.")

        if args.dry_run:
            print("Dry run - nothing deleted.")
            return 0

        if not doomed:
            print("Nothing to delete.")
            return 0

        conn.executemany(
            "DELETE FROM events WHERE id = ?", [(row["id"],) for row in doomed]
        )
        # The learning feature is gone; its table is dead weight full of course
        # records. Dropped here so one command leaves the database clean.
        conn.execute("DROP TABLE IF EXISTS learning_programs")
        conn.commit()
        remaining = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        print(f"Deleted {len(doomed)}. {remaining} events remain.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
