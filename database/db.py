"""
SQLite persistence layer.

Everything the dashboard knows lives in a single SQLite file - no other
database engine, no ORM. Connections are opened per call and closed straight
away, which keeps the scheduler thread and the web server thread from fighting
over one shared handle.
"""

import os
import sqlite3
from datetime import datetime, timedelta

from config import settings
from config.categories import OPPORTUNITY_GROUPS, STARTUP_FUNDING_CATEGORIES
from config.course_filter import is_course
from config.priority import (
    MIDDLE_EAST_COUNTRIES, PRIORITY_TAGS, assign_location, geo_score, match_tags,
)
from config.regions import INDIAN_STATES

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
    category         TEXT    NOT NULL DEFAULT 'Technology Event',
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

    -- Structured opportunity detail. Scraped events fill in what the page
    -- happens to expose; curated records (scripts/seed_opportunities.py) fill
    -- in everything that could be verified from the official source. Every
    -- one defaults to '' - an empty field means "not available", never a
    -- guess.
    subcategory      TEXT    DEFAULT '',
    description      TEXT    DEFAULT '',
    organizer        TEXT    DEFAULT '',
    start_date       TEXT    DEFAULT '',          -- YYYY-MM-DD
    end_date         TEXT    DEFAULT '',          -- YYYY-MM-DD
    deadline         TEXT    DEFAULT '',          -- application close, YYYY-MM-DD
    source_url       TEXT    DEFAULT '',          -- official event page
    application_url  TEXT    DEFAULT '',          -- register / apply / submit
    eligibility      TEXT    DEFAULT '',
    cost             TEXT    DEFAULT '',
    prize_or_funding TEXT    DEFAULT '',
    tags             TEXT    DEFAULT '',          -- comma separated
    is_verified      INTEGER NOT NULL DEFAULT 0,  -- 1 = fields checked against the official source
    last_verified_at TEXT    DEFAULT '',          -- YYYY-MM-DD of that check

    -- Priority ordering. See config/priority.py: `city` is read off the
    -- published location (never the title), `priority_tags` lists only the
    -- collections the record's own fields prove it belongs to, and
    -- `geo_score` is the deterministic key every listing is sorted on.
    city             TEXT    DEFAULT '',
    priority_tags    TEXT    DEFAULT '',
    geo_score        INTEGER NOT NULL DEFAULT 100
);

CREATE INDEX IF NOT EXISTS idx_events_is_new     ON events (is_new);
CREATE INDEX IF NOT EXISTS idx_events_date_iso   ON events (date_iso);
CREATE INDEX IF NOT EXISTS idx_events_category   ON events (category);
CREATE INDEX IF NOT EXISTS idx_events_created    ON events (created_at);

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


# Columns added after the first release. Applied by init_db() to databases
# that predate them; the names and types match the SCHEMA above.
ADDED_COLUMNS = {
    "focus": "INTEGER NOT NULL DEFAULT 0",
    "subcategory": "TEXT DEFAULT ''",
    "description": "TEXT DEFAULT ''",
    "organizer": "TEXT DEFAULT ''",
    "start_date": "TEXT DEFAULT ''",
    "end_date": "TEXT DEFAULT ''",
    "deadline": "TEXT DEFAULT ''",
    "source_url": "TEXT DEFAULT ''",
    "application_url": "TEXT DEFAULT ''",
    "eligibility": "TEXT DEFAULT ''",
    "cost": "TEXT DEFAULT ''",
    "prize_or_funding": "TEXT DEFAULT ''",
    "tags": "TEXT DEFAULT ''",
    "is_verified": "INTEGER NOT NULL DEFAULT 0",
    "last_verified_at": "TEXT DEFAULT ''",
    "city": "TEXT DEFAULT ''",
    "priority_tags": "TEXT DEFAULT ''",
    "geo_score": "INTEGER NOT NULL DEFAULT 100",
}


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

        # CREATE TABLE IF NOT EXISTS leaves an older table untouched, so every
        # column added after the first release has to be applied explicitly.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
        for name, ddl in ADDED_COLUMNS.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")

        # Indexes on the late-added columns go in after the ALTERs above -
        # on a pre-existing database the column does not exist until then.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_geo_score ON events (geo_score)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_region ON events (region)"
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

    Course listings are refused here as well as in the extractor. The extractor
    is the real filter; this is the backstop that guarantees no code path -
    a new adapter, a manual import, a backfill script - can put a course into
    the table.
    """
    if is_course(event.get("title", "")):
        return False

    # Sources disagree about what goes in `region` - some send a state, some
    # send "India", a city or a venue. Folding every location column onto the
    # one vocabulary here is what makes the Country / State / City filters
    # agree with each other for scraped records as well as curated ones, and
    # it is done from the location fields alone - never from the title.
    country, region, city, tier = assign_location(
        region=event.get("region", ""),
        country=event.get("country", ""),
        location=event.get("location", ""),
        mode=event.get("mode", ""),
    )
    tags = match_tags(
        event.get("title", ""), event.get("organizer", ""), event.get("source", ""),
        event.get("tags", ""), event.get("description", ""), event.get("category", ""),
    )
    score = geo_score(tier, city, tags)

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO events (
                title, category, location, date, date_iso, registration_url,
                website, source, status, mode, country, region,
                created_at, is_new, focus, fingerprint,
                city, priority_tags, geo_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event["title"],
                event.get("category", "Technology Event"),
                event.get("location", "Not specified"),
                event.get("date", ""),
                event.get("date_iso", ""),
                event.get("registration_url", ""),
                event.get("website", ""),
                event["source"],
                event.get("status", "Open"),
                event.get("mode", "Offline"),
                country,
                region,
                datetime.utcnow().isoformat(timespec="seconds"),
                1,                       # every freshly discovered event is new
                int(event.get("focus", 0)),
                event["fingerprint"],
                city,
                tags,
                score,
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
    Recompute `status` for every event from its dates.

    The application deadline decides it whenever one is known, because that is
    what "can I still apply?" actually depends on; the event date is the
    fallback for the many scraped listings that publish no deadline.

    Closed        -> the deadline (or, with none, the event date) has passed
    Closing Soon  -> that date falls within settings.CLOSING_SOON_DAYS
    Open          -> anything further out

    Events with neither date keep whatever status they were stored with -
    guessing "Open" for a listing we know nothing about would be a claim the
    data does not support.
    """
    today = datetime.utcnow().date()
    soon = today + timedelta(days=settings.CLOSING_SOON_DAYS)

    # COALESCE picks the deadline when there is one and the event date
    # otherwise; NULLIF turns the empty-string default into NULL so it does.
    effective = "COALESCE(NULLIF(deadline, ''), NULLIF(date_iso, ''))"

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE events SET status='Closed' "
            f"WHERE {effective} IS NOT NULL AND {effective} < ?",
            (today.isoformat(),),
        )
        conn.execute(
            f"""UPDATE events SET status='Closing Soon'
                WHERE {effective} IS NOT NULL
                  AND {effective} >= ? AND {effective} <= ?""",
            (today.isoformat(), soon.isoformat()),
        )
        conn.execute(
            f"UPDATE events SET status='Open' "
            f"WHERE {effective} IS NOT NULL AND {effective} > ?",
            (soon.isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()


def dedupe_events():
    """
    Collapse records that describe the same opportunity.

    The stored `fingerprint` includes the scraped date, so one event picked up
    twice - once before its date was published and once after, or from two
    source pages with slightly different names ("Game Developer" vs "Game
    Developers Conference") - lands in the table twice. That is invisible to
    the UNIQUE constraint but very visible on the events page.

    Grouping is on the punctuation-stripped lower-cased title. Within a group
    the row that carries the most information is kept (verified first, then
    the one with a date, then the most filled-in fields); the rest are
    deleted. Returns the number of rows removed.
    """
    def normalise(title):
        return "".join(ch for ch in (title or "").lower() if ch.isalnum())

    # Fields whose presence makes one copy more useful than another.
    detail_columns = (
        "date_iso", "deadline", "description", "organizer", "application_url",
        "source_url", "registration_url", "website", "subcategory", "tags",
        "eligibility", "prize_or_funding", "cost",
    )

    def richness(row):
        return (
            int(row["is_verified"] or 0),
            1 if (row["date_iso"] or "") else 0,
            sum(1 for c in detail_columns if (row[c] or "")),
            int(row["geo_score"] or 0),
            -int(row["id"]),          # oldest id wins a tie, so links stay put
        )

    conn = get_connection()
    try:
        groups = {}
        for row in conn.execute("SELECT * FROM events"):
            groups.setdefault(normalise(row["title"]), []).append(row)

        doomed = []
        for rows in groups.values():
            if len(rows) < 2:
                continue
            rows = sorted(rows, key=richness, reverse=True)
            doomed.extend(int(r["id"]) for r in rows[1:])

        for chunk_start in range(0, len(doomed), 500):
            chunk = doomed[chunk_start:chunk_start + 500]
            conn.execute(
                "DELETE FROM events WHERE id IN (%s)" % ", ".join("?" * len(chunk)),
                chunk,
            )
        conn.commit()
        return len(doomed)
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

def _row_to_dict(row):
    """Convert a sqlite3.Row into a plain JSON-serialisable dictionary."""
    return {key: row[key] for key in row.keys()}


# Filter labels that stand for several stored categories. The events page
# offers them because users think in these terms ("Startup Funding") even
# though the classifier files each listing under one narrower category.
CATEGORY_ALIASES = {
    "startup funding": STARTUP_FUNDING_CATEGORIES,
    "gaming": ["Gaming Event", "Game Jam"],
    "edtech": ["EdTech Event"],
    "technology": ["Technology Event"],
    "meetup": ["Networking"],
    "grant": ["Grant"],
    "hackathon": ["Hackathon"],
    **{label.lower(): cats for label, cats in OPPORTUNITY_GROUPS.items()},
}


def resolve_categories(label):
    """The stored category names one filter label selects."""
    if not label or label.lower() == "all":
        return []
    return CATEGORY_ALIASES.get(label.strip().lower(), [label])


SEARCH_COLUMNS = (
    "title", "category", "subcategory", "organizer", "description",
    "tags", "priority_tags", "location", "region", "city", "country", "source",
)

# Words users type that the stored text spells differently.
#
# "AR/VR" is the clear case: the classifier files XR listings under Gaming
# Event and the titles say "XR", "immersive" or "Vision Pro", so a literal
# search for "ar/vr" matched nothing at all. Each key expands to an OR over
# its variants; a term that is not a key is searched literally, unchanged.
#
# These are spelling variants of one subject, not a topic map. Nothing here
# makes a search return a listing that is not actually about the thing typed.
SEARCH_SYNONYMS = {
    "ar/vr": ["ar/vr", "ar vr", "xr", "augmented reality", "virtual reality",
              "mixed reality", "immersive", "metaverse", "spatial computing"],
    "arvr": ["ar/vr", "ar vr", "xr", "augmented reality", "virtual reality"],
    "ar": ["ar/vr", "augmented reality"],
    "vr": ["ar/vr", "virtual reality", "vr "],
    "xr": ["xr", "ar/vr", "immersive", "mixed reality"],
    "game jam": ["game jam", "gamejam"],
    "gamejam": ["game jam", "gamejam"],
    "meetup": ["meetup", "meet-up", "networking"],
    "edtech": ["edtech", "ed-tech", "education technology"],
    "startup funding": ["startup funding", "seed", "funding", "grant"],
}


def search_terms(search):
    """Every string a search box entry should be matched against."""
    term = " ".join(str(search or "").split()).lower()
    return SEARCH_SYNONYMS.get(term, [term]) if term else []


def build_where(
    only_new=False,
    since=None,
    focus_only=False,
    category=None,
    country=None,
    region=None,
    city=None,
    tag=None,
    provider=None,
    mode=None,
    status=None,
    upcoming=False,
    search=None,
):
    """
    Turn a set of filters into one SQL WHERE clause plus its bound parameters.

    Shared by query_events and get_stats, which is what makes the counters on
    a filtered page agree with the list underneath them - both are computed
    from exactly the same predicate rather than from two copies of it.
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

    wanted = resolve_categories(category)
    if wanted:
        clauses.append("category IN (%s)" % ", ".join("?" * len(wanted)))
        params.extend(wanted)

    if country and country.lower() != "all":
        if country.strip().lower() == "middle east":
            # A region rather than a country - expand it to its members so
            # the filter and the home page section select the same records.
            placeholders = ", ".join("?" * len(MIDDLE_EAST_COUNTRIES))
            clauses.append(f"country IN ({placeholders})")
            params.extend(MIDDLE_EAST_COUNTRIES)
        else:
            clauses.append("country = ?")
            params.append(country)

    if region and region.lower() != "all":
        clauses.append("region = ?")
        params.append(region)

    if city and city.lower() != "all":
        clauses.append("city = ?")
        params.append(city)

    if tag and tag.lower() != "all":
        # Stored as a comma separated list, so each wanted tag is matched
        # against ", <tags>," to keep "Hackathon" from matching a longer name.
        wanted_tags = [t.strip() for t in tag.split(",") if t.strip()]
        if wanted_tags:
            clauses.append(
                "(" + " OR ".join(
                    "(', ' || priority_tags || ',') LIKE ?" for _ in wanted_tags
                ) + ")"
            )
            params.extend(f"%, {t},%" for t in wanted_tags)

    if provider and provider.lower() != "all":
        clauses.append("source = ?")
        params.append(provider)

    if mode and mode.lower() != "all":
        clauses.append("mode = ?")
        params.append(mode)

    if status and status.lower() != "all":
        clauses.append("status = ?")
        params.append(status)

    if upcoming:
        # Keep events with a future date, plus events whose date we could not
        # parse (dropping those would hide real opportunities). Anything the
        # status logic has already called Closed is excluded whatever its
        # date says - an opportunity whose deadline has passed is not
        # upcoming, and listing it as such is the one thing this filter must
        # never do.
        clauses.append("status != 'Closed' AND (date_iso = '' OR date_iso >= ?)")
        params.append(datetime.utcnow().date().isoformat())

    # Searching is opportunity-based: "KSUM" has to find the organiser,
    # "grant" the category, "game jam" the tags and "Kochi" the location, not
    # just whatever happens to be in the title.
    terms = search_terms(search)
    if terms:
        # Every searchable column against every spelling of the term, OR-ed.
        ors = [
            f"LOWER(COALESCE({c},'')) LIKE ?"
            for _ in terms
            for c in SEARCH_COLUMNS
        ]
        clauses.append("(" + " OR ".join(ors) + ")")
        for term in terms:
            params.extend(["%" + term + "%"] * len(SEARCH_COLUMNS))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def query_events(order="priority", limit=500, **filters):
    """
    The single read used by every API endpoint.

    All filters are optional and combine with AND (see build_where for the
    full list). Values are passed as bound parameters, so a search term can
    never turn into SQL injection.

    `since` selects everything discovered at or after an ISO timestamp - it is
    what the New Events page uses once its badge has been cleared.
    `focus_only` keeps just the games / AR-VR / apps events.
    `tag` selects a priority collection (Sayuj / Huddle / Thinker / Hackathon
    / KSUM); several may be given comma separated and match as OR.
    """
    where, params = build_where(**filters)
    search = filters.get("search")

    today_iso = datetime.utcnow().date().isoformat()

    # The platform-wide default. Geography and the priority collections come
    # first (Kerala, then Sayuj / Huddle / Thinker / Hackathons, then Tamil
    # Nadu with Chennai ahead, Karnataka, India, Middle East, Japan), then the
    # secondary order the brief specifies: still-open events ahead of finished
    # ones, closing-soon next, soonest deadline, soonest start date, and
    # finally the newest verified records. Nothing is ordered alphabetically.
    priority_sql = (
        "ORDER BY geo_score DESC, "
        f"(date_iso = '' OR date_iso >= '{today_iso}') DESC, "
        "(status = 'Closing Soon') DESC, "
        "(deadline = '') ASC, deadline ASC, "
        "(date_iso = '') ASC, date_iso ASC, "
        "is_verified DESC, last_verified_at DESC, created_at DESC, id DESC"
    )

    if order == "recent":
        # Newest discoveries first, but still Kerala-first within a batch.
        order_sql = "ORDER BY created_at DESC, geo_score DESC, id DESC"
    elif order == "deadline":
        # Closing opportunities first - the one sort a user asks for by name.
        order_sql = (
            "ORDER BY (deadline = '') ASC, deadline ASC, "
            "(date_iso = '') ASC, date_iso ASC, geo_score DESC, id DESC"
        )
    elif order == "date":
        order_sql = (
            "ORDER BY (date_iso = '') ASC, date_iso ASC, geo_score DESC, id DESC"
        )
    elif order == "focus":
        # Games / AR-VR / apps first, then the standard priority order. This is
        # the default on the events page: nothing is hidden, but our work
        # comes first.
        order_sql = "ORDER BY focus DESC, " + priority_sql[len("ORDER BY "):]
    else:
        order_sql = priority_sql

    terms = search_terms(search)
    if terms:
        # Title hits outrank a match only found in category / tags / location.
        title_hit = " OR ".join("LOWER(title) LIKE ?" for _ in terms)
        order_sql = (
            f"ORDER BY ({title_hit}) DESC, {order_sql[len('ORDER BY '):]}"
        )
        params.extend("%" + t + "%" for t in terms)

    sql = f"SELECT * FROM events {where} {order_sql} LIMIT ?"
    params.append(int(limit))

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_event(event_id):
    """One event by id, or None. Backs the event details page."""
    try:
        event_id = int(event_id)
    except (TypeError, ValueError):
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def count_new_events():
    """Number badge for the 🔔 notification box."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE is_new = 1"
        ).fetchone()
        return row["c"]
    finally:
        conn.close()


def get_stats(**filters):
    """
    Summary numbers plus the values that populate the filter drop-downs.

    Every counter is computed over the *filtered* set, using the same
    build_where predicate the event list uses, so the numbers on screen always
    describe the list on screen. Called with no filters (the home page) it
    describes the whole table.

    The drop-down option lists are deliberately NOT filtered - narrowing them
    to the current selection would make it impossible to change a filter back.
    """
    where, base_params = build_where(**filters)
    scope = where or ""
    today = datetime.utcnow().date().isoformat()

    conn = get_connection()
    try:
        def count(extra_sql="", extra_params=()):
            """COUNT(*) over the filtered set, optionally narrowed further."""
            sql = f"SELECT COUNT(*) AS c FROM events {scope}"
            params = list(base_params)
            if extra_sql:
                sql += (" AND " if scope else " WHERE ") + extra_sql
                params.extend(extra_params)
            return conn.execute(sql, params).fetchone()["c"]

        total = count()
        new = count("is_new = 1")
        # Matches query_events(upcoming=True): an unparsed date is not proof
        # the event has passed, so those rows count as upcoming in both places.
        upcoming = count("status != 'Closed' AND (date_iso = '' OR date_iso >= ?)", (today,))
        closing = count("status = 'Closing Soon'")
        closed = count("status = 'Closed'")
        focus = count("focus > 0")

        countries = [
            r["country"]
            for r in conn.execute(
                "SELECT DISTINCT country FROM events WHERE country != '' ORDER BY country"
            )
        ]
        # The State drop-down lists Indian states, in the canonical order
        # (Kerala first), and only those that actually have events behind
        # them - so picking one never yields an empty list.
        stored_regions = {
            r["region"]
            for r in conn.execute(
                "SELECT DISTINCT region FROM events WHERE region != ''"
            )
        }
        regions = [name for name in INDIAN_STATES if name in stored_regions]

        # One count per home-page counter. Courses are not represented
        # because they are never stored.
        opportunities = {}
        for label, cats in OPPORTUNITY_GROUPS.items():
            placeholders = ", ".join("?" * len(cats))
            opportunities[label] = count(f"category IN ({placeholders})", cats)

        # One count per priority collection, and the cities that actually
        # have events, so the City filter never offers a dead option.
        tag_counts = {}
        for tag in PRIORITY_TAGS:
            tag_counts[tag] = count(
                "(', ' || priority_tags || ',') LIKE ?", (f"%, {tag},%",)
            )

        cities = [
            r["city"]
            for r in conn.execute(
                "SELECT city, COUNT(*) AS c FROM events WHERE city != '' "
                "GROUP BY city ORDER BY c DESC, city"
            )
        ]

        middle_east = count(
            "country IN (%s)" % ", ".join("?" * len(MIDDLE_EAST_COUNTRIES)),
            MIDDLE_EAST_COUNTRIES,
        )
        kerala = count("region = 'Kerala'")
        india = count("country = 'India'")

        providers = [
            r["source"]
            for r in conn.execute(
                "SELECT DISTINCT source FROM events WHERE source != '' ORDER BY source"
            )
        ]
        last_run = conn.execute(
            "SELECT * FROM crawl_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total": total,
            "new": new,
            "upcoming": upcoming,
            "closing_soon": closing,
            "closed": closed,
            "focus": focus,
            "opportunities": opportunities,
            "priority_tags": tag_counts,
            "cities": cities,
            "kerala": kerala,
            "india": india,
            "middle_east": middle_east,
            "countries": countries,
            "regions": regions,
            "providers": providers,
            "last_run": _row_to_dict(last_run) if last_run else None,
        }
    finally:
        conn.close()
