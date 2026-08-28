"""
SQLite persistence layer.

Everything the dashboard knows lives in a single SQLite file - no other
database engine, no ORM. Connections are opened per call and closed straight
away, which keeps the scheduler thread and the web server thread from fighting
over one shared handle.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta

from config import settings

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# `fingerprint` is the duplicate-detection key (a hash of source + normalised
# title + date). The UNIQUE constraint makes duplicates impossible even if two
# crawls somehow run at the same time.
SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    category         TEXT    NOT NULL DEFAULT 'Technology',
    location         TEXT    DEFAULT 'Not specified',
    date             TEXT    DEFAULT '',          -- human readable, as scraped
    date_iso         TEXT    DEFAULT '',          -- YYYY-MM-DD for sorting
    registration_url TEXT    DEFAULT '',
    website          TEXT    DEFAULT '',
    source           TEXT    NOT NULL,
    status           TEXT    DEFAULT 'Open',      -- Open / Closing Soon / Closed
    mode             TEXT    DEFAULT 'Offline',   -- Online / Offline
    country          TEXT    DEFAULT '',
    region           TEXT    DEFAULT '',
    created_at       TEXT    NOT NULL,
    is_new           INTEGER NOT NULL DEFAULT 1,
    focus            INTEGER NOT NULL DEFAULT 0,  -- 2/1/0, see classifier.focus_score
    fingerprint      TEXT    NOT NULL UNIQUE,

    -- ---- EdTech & Learning Programs ----------------------------------
    is_learning       INTEGER NOT NULL DEFAULT 0,  -- 1 = shows on the Learning tab
    categories        TEXT    DEFAULT '[]',        -- JSON list, e.g. ["EdTech","AI & Machine Learning"]
    program_type      TEXT    DEFAULT '',          -- Course / Bootcamp / Scholarship / ...
    funding_type      TEXT    DEFAULT '',          -- Free / Fully Funded / Scholarship / Paid / ...
    level             TEXT    DEFAULT '',          -- Beginner / Intermediate / Advanced / Professional
    format            TEXT    DEFAULT '',          -- Online / Offline / Hybrid
    duration          TEXT    DEFAULT '',          -- "1 day" / "1 week" / "1 month" / ...
    certificate       TEXT    DEFAULT 'Unknown',   -- Certificate available / No certificate / Unknown
    skills            TEXT    DEFAULT '[]',        -- JSON list
    career_paths      TEXT    DEFAULT '[]',        -- JSON list
    eligibility       TEXT    DEFAULT '{}',        -- JSON object
    official_url      TEXT    DEFAULT '',
    application_url   TEXT    DEFAULT '',
    source_url        TEXT    DEFAULT '',
    deadline          TEXT    DEFAULT '',          -- YYYY-MM-DD, application deadline
    start_date        TEXT    DEFAULT '',
    provider          TEXT    DEFAULT '',
    last_verified_at  TEXT    DEFAULT '',
    is_verified       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_is_new     ON events (is_new);
CREATE INDEX IF NOT EXISTS idx_events_date_iso   ON events (date_iso);
CREATE INDEX IF NOT EXISTS idx_events_category   ON events (category);
CREATE INDEX IF NOT EXISTS idx_events_created    ON events (created_at);
-- idx_events_is_learning / idx_events_funding_type are created after the
-- migration below adds those columns, so a database created before EdTech &
-- Learning Programs existed does not fail here with "no such column".

-- Small key/value store. Currently holds `new_batch_cutoff`, the timestamp
-- that keeps the New Events page showing its batch after the badge is cleared.
CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- One row per crawl, used by the dashboard to show "last checked" info.
CREATE TABLE IF NOT EXISTS crawl_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT,
    finished_at   TEXT,
    sources_ok    INTEGER DEFAULT 0,
    sources_failed INTEGER DEFAULT 0,
    new_events    INTEGER DEFAULT 0
);
"""


def get_connection():
    """Open a SQLite connection that returns dict-like rows."""
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL lets the web server read while the scraper writes.
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the tables the first time the app runs. Safe to call always."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)

        # Migration for databases created before the focus ranking existed.
        # CREATE TABLE IF NOT EXISTS leaves an older table untouched, so the
        # column has to be added explicitly.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
        if "focus" not in columns:
            conn.execute(
                "ALTER TABLE events ADD COLUMN focus INTEGER NOT NULL DEFAULT 0"
            )

        # Migration for databases created before EdTech & Learning Programs.
        learning_columns = {
            "is_learning": "INTEGER NOT NULL DEFAULT 0",
            "categories": "TEXT DEFAULT '[]'",
            "program_type": "TEXT DEFAULT ''",
            "funding_type": "TEXT DEFAULT ''",
            "level": "TEXT DEFAULT ''",
            "format": "TEXT DEFAULT ''",
            "duration": "TEXT DEFAULT ''",
            "certificate": "TEXT DEFAULT 'Unknown'",
            "skills": "TEXT DEFAULT '[]'",
            "career_paths": "TEXT DEFAULT '[]'",
            "eligibility": "TEXT DEFAULT '{}'",
            "official_url": "TEXT DEFAULT ''",
            "application_url": "TEXT DEFAULT ''",
            "source_url": "TEXT DEFAULT ''",
            "deadline": "TEXT DEFAULT ''",
            "start_date": "TEXT DEFAULT ''",
            "provider": "TEXT DEFAULT ''",
            "last_verified_at": "TEXT DEFAULT ''",
            "is_verified": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, ddl in learning_columns.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_is_learning ON events (is_learning)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_funding_type ON events (funding_type)"
        )

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Key/value store
# ---------------------------------------------------------------------------

def get_meta(key, default=None):
    """Read one value from the app_meta table."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_meta(key, value):
    """Write one value into the app_meta table."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO app_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def event_exists(fingerprint):
    """True when an event with this fingerprint was already stored."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM events WHERE fingerprint = ? LIMIT 1", (fingerprint,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def insert_event(event):
    """
    Insert one scraped event.

    Returns True when the row was actually written, False when it was a
    duplicate (the UNIQUE fingerprint constraint rejected it). Duplicate
    detection therefore happens at the database level and cannot be bypassed.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO events (
                title, category, location, date, date_iso, registration_url,
                website, source, status, mode, country, region,
                created_at, is_new, focus, fingerprint,
                is_learning, categories, program_type, funding_type, level,
                format, duration, certificate, skills, career_paths,
                eligibility, official_url, application_url, source_url,
                deadline, start_date, provider, last_verified_at, is_verified
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                      ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event["title"],
                event.get("category", "Technology"),
                event.get("location", "Not specified"),
                event.get("date", ""),
                event.get("date_iso", ""),
                event.get("registration_url", ""),
                event.get("website", ""),
                event["source"],
                event.get("status", "Open"),
                event.get("mode", "Offline"),
                event.get("country", ""),
                event.get("region", ""),
                datetime.utcnow().isoformat(timespec="seconds"),
                1,                       # every freshly discovered event is new
                int(event.get("focus", 0)),
                event["fingerprint"],
                int(event.get("is_learning", 0)),
                json.dumps(event.get("categories", [])),
                event.get("program_type", ""),
                event.get("funding_type", ""),
                event.get("level", ""),
                event.get("format", ""),
                event.get("duration", ""),
                event.get("certificate", "Unknown"),
                json.dumps(event.get("skills", [])),
                json.dumps(event.get("career_paths", [])),
                json.dumps(event.get("eligibility", {})),
                event.get("official_url", ""),
                event.get("application_url", ""),
                event.get("source_url", ""),
                event.get("deadline", ""),
                event.get("start_date", ""),
                event.get("provider", ""),
                event.get("last_verified_at", ""),
                int(event.get("is_verified", 0)),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Fingerprint already present -> the event is a duplicate, ignore it.
        return False
    finally:
        conn.close()


def mark_seen():
    """
    Clear the 🔔 badge and return the cutoff that identifies the batch the
    user is looking at.

    Opening the New Events page marks everything as seen, but the page must
    keep showing those events - otherwise the list empties out the moment a
    filter is changed or the page is reloaded. So before dropping the flags we
    remember when the oldest still-new event was discovered, and the page asks
    for `created_at >= cutoff` from then on instead of `is_new = 1`.

    A visit that finds nothing new leaves the stored cutoff alone, so coming
    back to the page still shows the same batch.

    Returns (cutoff_iso, cleared_count).
    """
    conn = get_connection()
    try:
        oldest = conn.execute(
            "SELECT MIN(created_at) AS c FROM events WHERE is_new = 1"
        ).fetchone()["c"]

        cleared = 0
        if oldest:
            cur = conn.execute("UPDATE events SET is_new = 0 WHERE is_new = 1")
            cleared = cur.rowcount
            conn.execute(
                "INSERT INTO app_meta (key, value) VALUES ('new_batch_cutoff', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (oldest,),
            )
            conn.commit()
            return oldest, cleared

        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = 'new_batch_cutoff'"
        ).fetchone()
        if row and row["value"]:
            return row["value"], 0
    finally:
        conn.close()

    # Nothing new and no history yet (fresh install): fall back to the standard
    # "new" window so the page shows recent discoveries rather than nothing.
    return (
        datetime.utcnow() - timedelta(hours=settings.NEW_EVENT_WINDOW_HOURS)
    ).isoformat(timespec="seconds"), 0


def expire_old_new_flags():
    """Drop the `is_new` badge from events older than the configured window."""
    cutoff = (
        datetime.utcnow() - timedelta(hours=settings.NEW_EVENT_WINDOW_HOURS)
    ).isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE events SET is_new = 0 WHERE is_new = 1 AND created_at < ?",
            (cutoff,),
        )
        conn.commit()
    finally:
        conn.close()


def refresh_statuses():
    """
    Recompute `status` for every event with a known date.

    Closed        -> the event date is in the past
    Closing Soon  -> starts within settings.CLOSING_SOON_DAYS
    Open          -> anything further out
    """
    today = datetime.utcnow().date()
    soon = today + timedelta(days=settings.CLOSING_SOON_DAYS)
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE events SET status='Closed' WHERE date_iso != '' AND date_iso < ?",
            (today.isoformat(),),
        )
        conn.execute(
            """UPDATE events SET status='Closing Soon'
               WHERE date_iso != '' AND date_iso >= ? AND date_iso <= ?""",
            (today.isoformat(), soon.isoformat()),
        )
        conn.execute(
            "UPDATE events SET status='Open' WHERE date_iso != '' AND date_iso > ?",
            (soon.isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()


def prune_old_events():
    """Delete events that finished long ago so the database stays small."""
    cutoff = (
        datetime.utcnow() - timedelta(days=settings.RETENTION_DAYS_AFTER_EVENT)
    ).date().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM events WHERE date_iso != '' AND date_iso < ?", (cutoff,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def record_crawl_run(started_at, finished_at, sources_ok, sources_failed, new_events):
    """Store one line of crawl history."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO crawl_runs
               (started_at, finished_at, sources_ok, sources_failed, new_events)
               VALUES (?,?,?,?,?)""",
            (started_at, finished_at, sources_ok, sources_failed, new_events),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

_JSON_COLUMNS = {"categories": [], "skills": [], "career_paths": [], "eligibility": {}}


def _row_to_dict(row):
    """Convert a sqlite3.Row into a plain JSON-serialisable dictionary."""
    data = {key: row[key] for key in row.keys()}
    for column, default in _JSON_COLUMNS.items():
        if column in data:
            try:
                data[column] = json.loads(data[column]) if data[column] else default
            except (TypeError, json.JSONDecodeError):
                data[column] = default
    return data


def query_events(
    only_new=False,
    since=None,
    focus_only=False,
    category=None,
    country=None,
    region=None,
    mode=None,
    status=None,
    upcoming=False,
    search=None,
    order="date",
    limit=500,
    is_learning=None,
    program_type=None,
    funding_type=None,
    level=None,
    fmt=None,
    certificate=None,
):
    """
    The single read used by every API endpoint.

    All filters are optional and combine with AND. Values are passed as bound
    parameters, so a search term can never turn into SQL injection.

    `since` selects everything discovered at or after an ISO timestamp - it is
    what the New Events page uses once its badge has been cleared.
    `focus_only` keeps just the games / AR-VR / apps events.
    """
    clauses = []
    params = []

    if only_new:
        clauses.append("is_new = 1")

    if since:
        clauses.append("created_at >= ?")
        params.append(since)

    if focus_only:
        clauses.append("focus > 0")

    if category and category.lower() != "all":
        clauses.append("category = ?")
        params.append(category)

    if country and country.lower() != "all":
        clauses.append("country = ?")
        params.append(country)

    if region and region.lower() != "all":
        clauses.append("region = ?")
        params.append(region)

    if mode and mode.lower() != "all":
        clauses.append("mode = ?")
        params.append(mode)

    if status and status.lower() != "all":
        clauses.append("status = ?")
        params.append(status)

    if upcoming:
        # Keep events with a future date, plus events whose date we could not
        # parse (dropping those would hide real opportunities).
        clauses.append("(date_iso = '' OR date_iso >= ?)")
        params.append(datetime.utcnow().date().isoformat())

    if is_learning is not None:
        clauses.append("is_learning = ?")
        params.append(1 if is_learning else 0)

    if program_type and program_type.lower() != "all":
        clauses.append("program_type = ?")
        params.append(program_type)

    if funding_type and funding_type.lower() != "all":
        clauses.append("funding_type = ?")
        params.append(funding_type)

    if level and level.lower() != "all":
        clauses.append("level = ?")
        params.append(level)

    if fmt and fmt.lower() != "all":
        clauses.append("format = ?")
        params.append(fmt)

    if certificate and certificate.lower() != "all":
        clauses.append("certificate = ?")
        params.append(certificate)

    if search:
        # Structured fields first (title/category/skills/programType/description
        # equivalents), matched as a single relevance-ordered LIKE clause.
        term = "%" + search.lower().strip() + "%"
        clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(category) LIKE ? OR LOWER(categories) LIKE ? "
            "OR LOWER(skills) LIKE ? OR LOWER(program_type) LIKE ?)"
        )
        params.extend([term, term, term, term, term])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    if order == "recent":
        # Newest discoveries first.
        order_sql = "ORDER BY created_at DESC, id DESC"
    elif order == "focus":
        # Games / AR-VR / apps first, then soonest date. This is the default on
        # the events page: nothing is hidden, but our work comes first.
        order_sql = (
            "ORDER BY focus DESC, (date_iso = '') ASC, date_iso ASC, created_at DESC"
        )
    else:
        # Soonest event first; undated events sink to the bottom.
        order_sql = "ORDER BY (date_iso = '') ASC, date_iso ASC, created_at DESC"

    if search:
        # Title hits outrank a match only found in category/skills/etc.
        term = "%" + search.lower().strip() + "%"
        order_sql = f"ORDER BY (LOWER(title) LIKE ?) DESC, {order_sql[len('ORDER BY '):]}"
        params.append(term)

    sql = f"SELECT * FROM events {where} {order_sql} LIMIT ?"
    params.append(int(limit))

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def count_new_events():
    """Number badge for the 🔔 notification box."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM events WHERE is_new = 1").fetchone()
        return row["c"]
    finally:
        conn.close()


def get_stats():
    """Summary numbers plus the values that populate the filter drop-downs."""
    today = datetime.utcnow().date().isoformat()
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        new = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_new = 1"
        ).fetchone()["c"]
        upcoming = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE date_iso >= ?", (today,)
        ).fetchone()["c"]
        closing = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE status = 'Closing Soon'"
        ).fetchone()["c"]
        focus = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE focus > 0"
        ).fetchone()["c"]

        countries = [
            r["country"]
            for r in conn.execute(
                "SELECT DISTINCT country FROM events WHERE country != '' ORDER BY country"
            )
        ]
        regions = [
            r["region"]
            for r in conn.execute(
                "SELECT DISTINCT region FROM events WHERE region != '' ORDER BY region"
            )
        ]
        last_run = conn.execute(
            "SELECT * FROM crawl_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        learning_total = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1"
        ).fetchone()["c"]
        learning_free = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1 "
            "AND funding_type IN ('Free', 'Free + Certificate')"
        ).fetchone()["c"]
        learning_scholarships = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1 AND funding_type = 'Scholarship'"
        ).fetchone()["c"]
        learning_fully_funded = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1 AND funding_type = 'Fully Funded'"
        ).fetchone()["c"]
        learning_certificates = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1 AND certificate = 'Certificate available'"
        ).fetchone()["c"]
        learning_closing_soon = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_learning = 1 AND status = 'Closing Soon'"
        ).fetchone()["c"]

        return {
            "total": total,
            "new": new,
            "upcoming": upcoming,
            "closing_soon": closing,
            "focus": focus,
            "countries": countries,
            "regions": regions,
            "last_run": _row_to_dict(last_run) if last_run else None,
            "learning": {
                "total": learning_total,
                "free": learning_free,
                "scholarships": learning_scholarships,
                "fully_funded": learning_fully_funded,
                "certificates": learning_certificates,
                "closing_soon": learning_closing_soon,
            },
        }
    finally:
        conn.close()
