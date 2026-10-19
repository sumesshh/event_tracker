"""
Rextech Studios - AI-powered Event Monitoring Dashboard
=======================================================

Single entry point. Running this one file:

  1. creates the SQLite database if it does not exist
  2. starts the background scheduler (crawls every 6 hours)
  3. serves the dashboard at http://127.0.0.1:8000

    python main.py              start everything (normal use)
    python main.py --crawl      run one crawl and exit, no web server
    python main.py --no-crawl   start the server without the startup crawl
"""

import sys
import webbrowser

from config import settings
from database import db
from scheduler.scheduler import start_scheduler
from server.app import run_server
from utils.logger import get_logger

log = get_logger("main")

BANNER = r"""
  ____           _            _       ____  _             _ _
 |  _ \ _____  _| |_ ___  ___| |__   / ___|| |_ _   _  __| (_) ___  ___
 | |_) / _ \ \/ / __/ _ \/ __| '_ \  \___ \| __| | | |/ _` | |/ _ \/ __|
 |  _ <  __/>  <| ||  __/ (__| | | |  ___) | |_| |_| | (_| | | (_) \__ \
 |_| \_\___/_/\_\\__\___|\___|_| |_| |____/ \__|\__,_|\__,_|_|\___/|___/

           Event Monitoring Dashboard - checks every 6 hours
"""


def main():
    """Wire the three pieces together and start serving."""
    print(BANNER)

    # 1. Database first - both the scraper and the server need the tables.
    db.init_db()
    log.info("Database ready at %s", settings.DATABASE_PATH)

    # The curated opportunities are no longer seeded on startup. They were a
    # hand-written stand-in for an empty dashboard, and a stand-in that never
    # expires is worse than an empty section: it shows programmes whose dates
    # have passed as though they were still open. Everything on the dashboard
    # now comes from a crawl. scripts/seed_opportunities.py still works if the
    # curated set is ever wanted again - run it by hand.

    # --crawl: one-off crawl for testing or for an external cron job.
    if "--crawl" in sys.argv:
        from scraper.runner import run_crawl
        result = run_crawl()
        log.info("Done. %d new events stored.", result.get("new_events", 0))
        return

    # --no-crawl: skip the startup crawl (useful when restarting often).
    if "--no-crawl" in sys.argv:
        settings.RUN_SCRAPE_ON_STARTUP = False

    # 2. Background scheduler - crawls now, then every 6 hours.
    start_scheduler()

    # 3. Open the dashboard in the default browser for convenience.
    url = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    try:
        webbrowser.open(url)
    except Exception:                              # noqa: BLE001 - headless is fine
        pass

    # 4. Serve until Ctrl+C.
    run_server()


if __name__ == "__main__":
    main()
