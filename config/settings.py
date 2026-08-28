"""
Global configuration for the Rextech Studios Event Dashboard.

Every value here is free to use - no paid APIs, no keys, no accounts.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Absolute path of the project root (the folder that contains main.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite database file. SQLite only - no other database engine is used.
# Overridable via $DATABASE_PATH so a persistent disk (e.g. Render's Disk
# add-on, mounted at /var/data) can be used without touching this file -
# see render.yaml.
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH", os.path.join(BASE_DIR, "database", "events.db")
)

# Folder holding the static frontend (HTML / CSS / JS)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Rotating log file written by the scraper and the scheduler
LOG_PATH = os.path.join(BASE_DIR, "logs", "app.log")


# ---------------------------------------------------------------------------
# Web server (pure Python http.server - no Django, no FastAPI)
# ---------------------------------------------------------------------------

# Render (and most hosts) assign the port at runtime via $PORT and expect the
# server to bind every interface (0.0.0.0), not just localhost. Locally,
# neither env var is set, so this falls back to the original 127.0.0.1:8000.
SERVER_HOST = os.environ.get("HOST", "127.0.0.1" if "PORT" not in os.environ else "0.0.0.0")
SERVER_PORT = int(os.environ.get("PORT", 8000))


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

# How often the crawler re-visits every source website (in hours).
SCRAPE_INTERVAL_HOURS = 6

# Run one crawl immediately when the application starts, so the dashboard is
# never empty on a fresh install.
RUN_SCRAPE_ON_STARTUP = True


# ---------------------------------------------------------------------------
# HTTP fetching behaviour
# ---------------------------------------------------------------------------

# Pretend to be a normal desktop browser; many sites block the default
# python-requests user agent.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Seconds to wait for a response before giving up on a source.
REQUEST_TIMEOUT = 20

# Seconds to pause between two requests, so we stay a polite crawler.
REQUEST_DELAY = 1.5

# How many times a failed request is retried before the source is skipped.
MAX_RETRIES = 2

# Playwright is only used for sources explicitly flagged `js_required=True`
# in config/sources.py. If Playwright is not installed those sources are
# simply skipped instead of crashing the crawl.
ENABLE_PLAYWRIGHT = True

# Milliseconds Playwright waits for client-side rendering to settle.
PLAYWRIGHT_WAIT_MS = 4000


# ---------------------------------------------------------------------------
# Data rules
# ---------------------------------------------------------------------------

# An event stays flagged with is_new = 1 for this many hours after insertion.
NEW_EVENT_WINDOW_HOURS = 48

# "Registration Closing Soon" = event starts within this many days.
CLOSING_SOON_DAYS = 14

# Events that finished more than this many days ago are pruned from the DB.
RETENTION_DAYS_AFTER_EVENT = 30

# Upper bound of items kept per source per crawl (protects against a page
# whose markup makes the extractor over-match).
MAX_EVENTS_PER_SOURCE = 40
