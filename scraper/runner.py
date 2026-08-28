"""
The crawl itself: visit every source, extract events, store the new ones.

This is the module the scheduler calls every 6 hours. It is also runnable on
its own for testing:

    python -m scraper.runner
"""

import time
import threading
from datetime import datetime

from config import settings
from config.sources import get_sources
from database import db
from scraper.extractor import extract_events
from scraper.fetcher import fetch
from utils.logger import get_logger

log = get_logger("runner")

# Guarantees that two crawls never overlap - if the scheduler fires while a
# manual refresh is still running, the second one simply returns.
_crawl_lock = threading.Lock()


def scrape_source(source):
    """
    Crawl one website.

    Returns (list_of_events, ok) where ok is False when the page could not be
    fetched at all, so the caller can count failures.
    """
    log.info("Checking %s (%s)", source["name"], source["url"])

    html = fetch(source)
    if not html:
        log.warning("No HTML from %s", source["name"])
        return [], False

    try:
        events = extract_events(html, source)
    except Exception as exc:                      # noqa: BLE001 - one bad page must
        log.exception("Extraction failed for %s: %s", source["name"], exc)
        return [], False                          # not stop the whole crawl

    return events, True


def run_crawl():
    """
    Visit every configured website once and insert everything new.

    Steps, in order:
      1. fetch + extract each source
      2. insert events whose fingerprint is not already in SQLite
         (duplicates are ignored - never inserted twice)
      3. recompute Open / Closing Soon / Closed statuses
      4. expire stale is_new badges and prune finished events
    """
    if not _crawl_lock.acquire(blocking=False):
        log.info("A crawl is already running - skipping this trigger")
        return {"skipped": True, "new_events": 0}

    started_at = datetime.utcnow().isoformat(timespec="seconds")
    log.info("=" * 60)
    log.info("Crawl started at %s UTC", started_at)

    sources_ok = 0
    sources_failed = 0
    total_found = 0
    total_new = 0

    try:
        for source in get_sources():
            events, ok = scrape_source(source)

            if ok:
                sources_ok += 1
            else:
                sources_failed += 1

            total_found += len(events)

            for event in events:
                # insert_event returns False for duplicates, so this counter
                # only ever grows on genuinely new discoveries.
                if db.insert_event(event):
                    total_new += 1
                    log.info("  NEW  [%s] %s", event["category"], event["title"][:80])

            # Stay a polite crawler.
            time.sleep(settings.REQUEST_DELAY)

        # Housekeeping after every crawl.
        # dedupe_events runs here because the fingerprint includes the scraped
        # date: the same opportunity picked up once before its date was
        # published and again afterwards passes the UNIQUE constraint as two
        # rows, and only a title-level pass catches that.
        db.refresh_statuses()
        db.expire_old_new_flags()
        merged = db.dedupe_events()
        pruned = db.prune_old_events()

        finished_at = datetime.utcnow().isoformat(timespec="seconds")
        db.record_crawl_run(started_at, finished_at, sources_ok, sources_failed, total_new)

        log.info(
            "Crawl finished: %d sources ok, %d failed, %d candidates, %d new, "
            "%d duplicates merged, %d pruned",
            sources_ok, sources_failed, total_found, total_new, merged, pruned,
        )
        log.info("=" * 60)

        return {
            "skipped": False,
            "sources_ok": sources_ok,
            "sources_failed": sources_failed,
            "found": total_found,
            "new_events": total_new,
        }
    finally:
        _crawl_lock.release()


if __name__ == "__main__":
    # Allow a one-off crawl straight from the command line.
    db.init_db()
    run_crawl()
