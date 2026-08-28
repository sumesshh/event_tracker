"""
The 6-hour scheduler.

Implemented with a plain daemon thread and time.sleep - no Celery, no cron,
no paid service. Because it is a daemon thread it dies automatically when the
web server stops, so Ctrl+C cleanly shuts the whole application down.
"""

import threading
import time
from datetime import datetime, timedelta

from config import settings
from scraper.runner import run_crawl
from utils.logger import get_logger

log = get_logger("scheduler")

# Timestamp of the next planned crawl, exposed to the dashboard via /api/stats.
_next_run_at = None


def get_next_run_at():
    """ISO timestamp of the next scheduled crawl, or None before it starts."""
    return _next_run_at


def _loop():
    """Crawl, sleep for the configured interval, repeat forever."""
    global _next_run_at

    interval_seconds = settings.SCRAPE_INTERVAL_HOURS * 3600

    if settings.RUN_SCRAPE_ON_STARTUP:
        log.info("Running the startup crawl so the dashboard is not empty")
        try:
            run_crawl()
        except Exception as exc:                  # noqa: BLE001
            log.exception("Startup crawl failed: %s", exc)

    while True:
        _next_run_at = (
            datetime.utcnow() + timedelta(seconds=interval_seconds)
        ).isoformat(timespec="seconds")
        log.info("Next crawl scheduled for %s UTC", _next_run_at)

        time.sleep(interval_seconds)

        try:
            run_crawl()
        except Exception as exc:                  # noqa: BLE001 - the scheduler must
            log.exception("Scheduled crawl failed: %s", exc)   # survive any failure


def start_scheduler():
    """Start the background crawl loop and return the thread."""
    thread = threading.Thread(target=_loop, name="rextech-scheduler", daemon=True)
    thread.start()
    log.info("Scheduler started - crawling every %d hours",
             settings.SCRAPE_INTERVAL_HOURS)
    return thread


def _manual_crawl():
    """Run the crawl for the Refresh button."""
    try:
        run_crawl()
    except Exception as exc:                      # noqa: BLE001
        log.exception("Manual crawl failed: %s", exc)


def trigger_now():
    """
    Run a crawl immediately in the background (used by the Refresh button).

    Returns False when a crawl is already in progress.
    """
    thread = threading.Thread(target=_manual_crawl, name="rextech-manual-crawl",
                              daemon=True)
    thread.start()
    return True
